"""LongMemEval 检索 benchmark：评测 Counterpart 记忆库的会话级召回。

==============================================================================
数据集下载说明（无需运行本脚本即可下载）
==============================================================================

LongMemEval (ICLR 2025, arxiv.org/abs/2410.10813) 是评测 chat assistant
长期记忆的标准 benchmark。500 道人工标注题，埋在可伸缩的 user-assistant
对话历史里，测 5 项能力：信息抽取 / 多会话推理 / 时间推理 / 知识更新 / 弃权。

官方数据集在 HuggingFace，仓库 `xiaowu0162/longmemeval-cleaned`
（cleaned 版本去掉了原始 release 里的脏数据，社区普遍用这个）：

    https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned

三个变体（本脚本默认用 Small）：
    longmemeval_s_cleaned.json        ~115K tokens/题, ~48 sessions/题  ← 推荐
    longmemeval_m_cleaned.json       ~1.5M tokens/题, ~500 sessions/题
    longmemeval_oracle_cleaned.json  只含 evidence sessions（对照组）

下载方式 A（推荐，用 huggingface_hub）：

    pip install huggingface_hub
    python -c "
    from huggingface_hub import hf_hub_download
    hf_hub_download(
        repo_id='xiaowu0162/longmemeval-cleaned',
        filename='longmemeval_s_cleaned.json',
        repo_type='dataset',
        local_dir='evals/data',
    )
    "

下载方式 B（直接 wget，无需装包）：

    mkdir -p evals/data
    wget -P evals/data \
      https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json

原始（未清洗）版本：https://huggingface.co/datasets/xiaowu0162/longmemeval
官方 repo：https://github.com/xiaowu0162/LongMemEval

数据集字段（每条 instance）：
    question_id            题目唯一 id（以 _abs 结尾的是弃权题）
    question_type          题型（single-session-user / multi-session /
                           temporal-reasoning / knowledge-update / ...）
    question               问题文本（作为检索 query）
    answer                 期望答案（本脚本不用，QA 评测才用）
    question_date          问题时间戳
    haystack_session_ids  所有历史 session 的 id 列表（按时间排序）
    haystack_dates        每个 session 的时间戳
    haystack_sessions     每个 session 的 turns 列表，turn =
                           {"role": "user"/"assistant", "content": "...",
                            "has_answer": bool}
    answer_session_ids    gold：含答案证据的 session id 列表（ground truth）

评测指标
    Recall@K (R@K)：top-K 检索结果里是否命中任意一个 gold session id。
        hit = len(retrieved_topK_session_ids ∩ answer_session_ids) > 0
    主指标 R@5。弃权题（answer_session_ids 为空）不计入 R@K，单独统计。

参考分数（同样 embedding + 纯检索，非端到端 QA）：
    MemPalace (ChromaDB raw, all-MiniLM-L6-v2)   R@5 = 96.6%
    Awareness Memory (Hybrid RRF, e5-small)       R@5 = 96.0%
    agentmemory (BM25+Vector, all-MiniLM-L6-v2)  R@5 = 95.2%

==============================================================================
用法
==============================================================================

    cd backend
    # 全量（500 题，慢，~30-60 min 取决于 embedding 速度）
    python -m evals.longmemeval_bench --data evals/data/longmemeval_s_cleaned.json
    # 快速测试（前 10 题）
    python -m evals.longmemeval_bench --data evals/data/longmemeval_s_cleaned.json --limit 10
    # 同时索引 turn 级 facts（更细粒度，但更慢）
    python -m evals.longmemeval_bench --data ... --with-facts
    # 跳过 R@10，只算 R@5（更快）
    python -m evals.longmemeval_bench --data ... --k 5

重要：embedding 模型决定分数上限。
    项目默认本地模型 BAAI/bge-small-zh-v1.5 是中文模型，对英文 LongMemEval
    会严重失真。要拿到接近 MemPalace 96.6% 的分数，请在 .env 设：
        EMBEDDING_API_URL=https://api.siliconflow.cn/v1/embeddings
        EMBEDDING_API_KEY=硅基流动 key
        EMBEDDING_API_MODEL=BAAI/bge-m3   # 多语言，英文表现好
    或改 EMBEDDING_MODEL=all-MiniLM-L6-v2（本地，英文专用，384 维）。

隔离性：本脚本把 DB_PATH / CHROMA_PATH 指到 evals/.bench_data/，
    不会动你生产的 memory.db 和 chroma/。每题之间会清空索引，互不污染。

设计参考：app/evals/run_eval.py（代码风格）、app/services/memory.py（检索 API）。
"""
import os

# ---- 隔离的 benchmark 数据目录（必须在 import app.* 之前设置）----
# 强制指向 evals/.bench_data/，绝不写生产库 memory.db / chroma/。
# LongMemEval 方法论要求每题 fresh index，隔离是方法论 + 安全双重要求。
from pathlib import Path as _Path

_EVAL_DIR = _Path(__file__).resolve().parent
_BENCH_DATA_DIR = _EVAL_DIR / ".bench_data"
_BENCH_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["DB_PATH"] = str(_BENCH_DATA_DIR / "bench.db")
os.environ["CHROMA_PATH"] = str(_BENCH_DATA_DIR / "chroma")

import argparse
import json
import logging
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app import database, vector_store
from app.config import settings
from app.services import memory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("longmemeval")

EVAL_DIR = Path(__file__).resolve().parent
REPORTS_DIR = EVAL_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# 数据集加载
# =============================================================================

def load_dataset(path: str) -> List[dict]:
    """加载 LongMemEval JSON 文件，返回 instance 列表（500 条）。

    支持 JSON 数组或 JSONL（每行一个 JSON 对象）。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"数据集不存在: {p}\n"
            "下载方法见本脚本 docstring（huggingface: xiaowu0162/longmemeval-cleaned）"
        )
    text = p.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped and stripped[0] == "[":
        data = json.loads(text)
    else:
        # JSONL
        data = [json.loads(line) for line in text.splitlines() if line.strip()]
    logger.info("加载 %d 条 instance（来自 %s）", len(data), p)
    return data


def session_to_text(session: List[dict], with_dates: bool = False,
                     session_date: Optional[str] = None) -> str:
    """把一个 session 的 turns 拼成纯文本，作为 episode 的 summary。

    LongMemEval 的 turn = {"role", "content", "has_answer"(可选)。
    """
    parts = []
    if with_dates and session_date:
        parts.append(f"[{session_date}]")
    for turn in session:
        role = turn.get("role", "unknown")
        content = turn.get("content", "")
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


# =============================================================================
# 索引管理（隔离的 bench 索引）
# =============================================================================

def init_bench_store() -> None:
    """初始化 benchmark 专用 SQLite + ChromaDB（幂等）。"""
    database.init_db()
    vector_store.init_vector_store()
    logger.info("bench 索引就绪: DB=%s chroma=%s", settings.db_path, settings.chroma_path)


def reset_bench_index() -> None:
    """清空 episodes / facts / reflections 三个 collection + 对应 SQLite 表。

    每题之间调用，保证索引互不污染。frameworks 不动（seed 预置的只读层）。
    """
    client = vector_store.get_client()
    for coll_name in (
        vector_store.COLLECTION_EPISODES,
        vector_store.COLLECTION_FACTS,
        vector_store.COLLECTION_REFLECTIONS,
    ):
        try:
            client.delete_collection(coll_name)
        except Exception:
            # collection 还不存在，忽略
            pass
        # 重新创建空 collection（保持 embedding_function / cosine 配置一致）
        vector_store.get_collection(coll_name)

    conn = database.get_db()
    try:
        conn.executescript(
            "DELETE FROM episodes;"
            "DELETE FROM facts;"
            "DELETE FROM reflections;"
            "DELETE FROM conversations;"
            "DELETE FROM messages;"
        )
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# 灌入 + 检索
# =============================================================================

def ingest_haystack(instance: dict, with_dates: bool = False,
                     with_facts: bool = False) -> int:
    """把 instance 的 haystack_sessions 灌入记忆库。

    - 每个 session → 1 个 episode（conversation_id = session_id，
      检索后从 metadata 取回，用于匹配 gold answer_session_ids）
    - with_facts=True 时，每个 turn → 1 个 fact（category = session_id，
      用 category 字段把 session_id 透传到 facts metadata）

    返回灌入的 episode 数。
    """
    session_ids = instance.get("haystack_session_ids", [])
    sessions = instance.get("haystack_sessions", [])
    dates = instance.get("haystack_dates", [])

    # 先建一个 conversation 容器（episodes 的 conversation_id 直接放 session_id，
    # 这里只是确保 conversations 表里有占位，方便人肉排查；非必须）
    n_episodes = 0
    for idx, session in enumerate(sessions):
        sid = session_ids[idx] if idx < len(session_ids) else f"sess_{idx}"
        sdate = dates[idx] if idx < len(dates) else None
        text = session_to_text(session, with_dates=with_dates, session_date=sdate)
        if not text.strip():
            continue
        memory.add_episode(
            conversation_id=sid,
            summary=text,
            importance=0.5,
            topics=[],
            entities=[],
        )
        n_episodes += 1

        if with_facts:
            for turn in session:
                role = turn.get("role", "unknown")
                content = turn.get("content", "")
                if not content.strip():
                    continue
                # category 复用为 session_id 载体（add_fact metadata 只有 category + importance）
                memory.add_fact(
                    category=sid,
                    content=f"{role}: {content}",
                    importance=0.5,
                    source="longmemeval_turn",
                )
    return n_episodes


def retrieve_topk(question: str, k: int, with_facts: bool) -> Tuple[List[dict], List[dict], List[dict]]:
    """对一个问题跑三层检索，各返回最多 k 条命中。

    episodes / facts 的每条 hit 标准化为：
        {"session_id": str, "score": float, "layer": "episodes"/"facts", "content": str}
    reflections 在纯检索 benchmark 里没有数据（需要 LLM 抽取），返回原始空结果，
    供上层报告"reflections 层未灌入"。
    """
    ep_hits = memory.search_episodes(question, n=k)
    ep = [
        {
            "session_id": h.get("metadata", {}).get("conversation_id", ""),
            "score": h.get("score") or 0.0,
            "layer": "episodes",
            "content": h.get("content", ""),
        }
        for h in ep_hits
    ]

    fa = []
    if with_facts:
        fa_hits = memory.search_facts(question, n=k)
        fa = [
            {
                "session_id": h.get("metadata", {}).get("category", ""),
                "score": h.get("score") or 0.0,
                "layer": "facts",
                "content": h.get("content", ""),
            }
            for h in fa_hits
        ]

    # reflections：纯检索 benchmark 不灌入（无 LLM 抽取），仍调用以覆盖 API
    rf_raw = memory.search_reflections(question, n=k)
    return ep, fa, rf_raw


def fuse_topk(episodes: List[dict], facts: List[dict], k: int) -> List[dict]:
    """episodes + facts 合并、按 session_id 去重（取 max score）、取 top-k。

    参考 memory.search_all 的合并方式：跨层结果按 score 降序。
    """
    best: Dict[str, dict] = {}
    for h in episodes + facts:
        sid = h.get("session_id", "")
        if not sid:
            continue
        prev = best.get(sid)
        if prev is None or (h.get("score", 0.0) > prev.get("score", 0.0)):
            best[sid] = h
    ranked = sorted(best.values(), key=lambda x: x.get("score", 0.0), reverse=True)
    return ranked[:k]


# =============================================================================
# 评分
# =============================================================================

def recall_at_k(retrieved_session_ids: List[str], gold: List[str], k: int) -> bool:
    """R@K：top-K 里是否命中任意一个 gold session id。"""
    if not gold:
        return False  # 弃权题单独处理
    topk = retrieved_session_ids[:k]
    return any(sid in gold for sid in topk)


def score_instance(instance: dict, ep: List[dict], fa: List[dict],
                   fused: List[dict], k_list: List[int]) -> dict:
    """对单题算各层的 R@k。"""
    gold = instance.get("answer_session_ids", []) or []
    is_abstention = (len(gold) == 0) or instance.get("question_id", "").endswith("_abs")

    ep_sids = [h["session_id"] for h in ep if h.get("session_id")]
    fa_sids = [h["session_id"] for h in fa if h.get("session_id")]
    fused_sids = [h["session_id"] for h in fused if h.get("session_id")]

    def rk(sids, k):
        return recall_at_k(sids, gold, k) if not is_abstention else False

    return {
        "question_id": instance.get("question_id", ""),
        "question_type": instance.get("question_type", ""),
        "is_abstention": is_abstention,
        "gold_count": len(gold),
        "k_hits": {
            "episodes": {k: rk(ep_sids, k) for k in k_list},
            "facts": {k: rk(fa_sids, k) for k in k_list},
            "fused": {k: rk(fused_sids, k) for k in k_list},
        },
    }


# =============================================================================
# 主流程
# =============================================================================

def run_bench(data_path: str, limit: Optional[int] = None,
              with_dates: bool = False, with_facts: bool = False,
              k_list: Optional[List[int]] = None) -> dict:
    """跑全量评测，返回统计结果。"""
    k_list = k_list or [1, 3, 5, 10]
    data = load_dataset(data_path)
    if limit:
        data = data[:limit]
        logger.info("限制前 %d 题（--limit %d）", limit, limit)

    init_bench_store()

    results = []
    t0 = time.time()
    for i, inst in enumerate(data, 1):
        qid = inst.get("question_id", f"#{i}")
        qtype = inst.get("question_type", "?")
        logger.info("[%d/%d] %s (%s) 灌入+检索...", i, len(data), qid, qtype)
        try:
            reset_bench_index()
            n_ep = ingest_haystack(inst, with_dates=with_dates, with_facts=with_facts)
            k_max = max(k_list)
            ep, fa, _rf = retrieve_topk(inst.get("question", ""), k=k_max, with_facts=with_facts)
            fused = fuse_topk(ep, fa, k=k_max)
            sc = score_instance(inst, ep, fa, fused, k_list)
            sc["n_episodes"] = n_ep
            # 主指标命中标记（用于日志）
            hit5 = sc["k_hits"]["fused"].get(5, False)
            logger.info("  → R@5=%s  (episodes=%d)", "HIT" if hit5 else "miss", n_ep)
            results.append(sc)
        except Exception as e:
            logger.error("  题 %s 执行失败: %s", qid, e)
            results.append({
                "question_id": qid,
                "question_type": qtype,
                "is_abstention": False,
                "gold_count": 0,
                "k_hits": {"episodes": {}, "facts": {}, "fused": {}},
                "n_episodes": 0,
                "error": str(e),
            })

    elapsed = time.time() - t0

    # ---- 汇总 ----
    def agg(layer, k):
        valid = [r for r in results if not r.get("is_abstention") and not r.get("error")]
        if not valid:
            return 0.0
        hits = sum(1 for r in valid if r["k_hits"].get(layer, {}).get(k, False))
        return hits / len(valid)

    valid_results = [r for r in results if not r.get("is_abstention") and not r.get("error")]
    abstention_count = sum(1 for r in results if r.get("is_abstention"))
    error_count = sum(1 for r in results if r.get("error"))

    # 按题型分桶（fused R@5）
    by_type = defaultdict(lambda: {"total": 0, "hits": 0})
    for r in valid_results:
        qtype = r.get("question_type", "?")
        by_type[qtype]["total"] += 1
        if r["k_hits"].get("fused", {}).get(5, False):
            by_type[qtype]["hits"] += 1

    stats = {
        "data_path": data_path,
        "limit": limit,
        "with_dates": with_dates,
        "with_facts": with_facts,
        "k_list": k_list,
        "embedding_info": _embedding_info(),
        "total": len(results),
        "valid_count": len(valid_results),
        "abstention_count": abstention_count,
        "error_count": error_count,
        "elapsed_sec": elapsed,
        "overall": {
            layer: {k: agg(layer, k) for k in k_list}
            for layer in ("episodes", "facts", "fused")
        },
        "by_type": {
            qtype: {
                "total": v["total"],
                "r5": v["hits"] / v["total"] if v["total"] else 0.0,
            }
            for qtype, v in sorted(by_type.items())
        },
        "results": results,
    }
    return stats


def _embedding_info() -> str:
    """拼出当前 embedding 配置描述，写入报告。"""
    if settings.embedding_api_url:
        return f"API: {settings.embedding_api_url} (model={settings.embedding_api_model})"
    return f"local: {settings.embedding_model}"


# =============================================================================
# 报告
# =============================================================================

def print_report(stats: dict) -> None:
    """打印到控制台。"""
    print("\n" + "=" * 64)
    print("Counterpart · LongMemEval 检索 benchmark 报告")
    print("=" * 64)
    print(f"数据集:        {stats['data_path']}")
    print(f"题数:          {stats['total']}  (有效 {stats['valid_count']}, "
          f"弃权 {stats['abstention_count']}, 失败 {stats['error_count']})")
    print(f"embedding:     {stats['embedding_info']}")
    print(f"with_facts:    {stats['with_facts']}  with_dates: {stats['with_dates']}")
    print(f"耗时:          {stats['elapsed_sec']:.1f}s  "
          f"({stats['elapsed_sec'] / max(stats['total'], 1):.1f}s/题)")
    print()
    print("Overall Recall@K (fused = episodes + facts 合并):")
    print(f"  {'K':<6} {'episodes':<12} {'facts':<12} {'fused':<12}")
    for k in stats["k_list"]:
        ep = stats["overall"]["episodes"].get(k, 0.0)
        fa = stats["overall"]["facts"].get(k, 0.0)
        fu = stats["overall"]["fused"].get(k, 0.0)
        print(f"  R@{k:<4} {ep:<12.1%} {fa:<12.1%} {fu:<12.1%}")
    print()
    print("R@5 by question_type (fused):")
    for qtype, v in stats["by_type"].items():
        print(f"  {qtype:<32} {v['r5']:<6.1%} (n={v['total']})")
    print("=" * 64)
    print("参考: MemPalace 96.6% / Awareness 96.0% / agentmemory 95.2% (R@5, 纯检索)")


def save_report(stats: dict) -> str:
    """保存 Markdown 报告到 evals/reports/。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"longmemeval_{ts}.md"

    lines = [
        f"# Counterpart · LongMemEval 检索 benchmark 报告 · {ts}",
        "",
        "## 配置",
        "",
        f"| 项 | 值 |",
        f"|---|---|",
        f"| 数据集 | `{stats['data_path']}` |",
        f"| 题数 | {stats['total']}（有效 {stats['valid_count']}，"
        f"弃权 {stats['abstention_count']}，失败 {stats['error_count']}）|",
        f"| limit | {stats['limit']} |",
        f"| with_dates | {stats['with_dates']} |",
        f"| with_facts | {stats['with_facts']} |",
        f"| embedding | {stats['embedding_info']} |",
        f"| 耗时 | {stats['elapsed_sec']:.1f}s "
        f"({stats['elapsed_sec'] / max(stats['total'], 1):.1f}s/题) |",
        "",
        "## 总体 Recall@K",
        "",
        f"| K | episodes | facts | fused (episodes+facts) |",
        f"|---|---|---|---|",
    ]
    for k in stats["k_list"]:
        ep = stats["overall"]["episodes"].get(k, 0.0)
        fa = stats["overall"]["facts"].get(k, 0.0)
        fu = stats["overall"]["fused"].get(k, 0.0)
        lines.append(f"| R@{k} | {ep:.1%} | {fa:.1%} | {fu:.1%} |")

    lines.extend([
        "",
        "## R@5 by question_type (fused)",
        "",
        "| 题型 | R@5 | 样本数 |",
        "|---|---|---|",
    ])
    for qtype, v in stats["by_type"].items():
        lines.append(f"| {qtype} | {v['r5']:.1%} | {v['total']} |")

    lines.extend([
        "",
        "## 方法论说明",
        "",
        "- **指标**：Recall@K = top-K 检索结果中是否命中任意一个 gold session id。"
        "纯检索评测，无 LLM 生成答案、无 judge。",
        "- **灌入**：每个 haystack session → 1 个 `episode`（`conversation_id` = session_id）。"
        "`--with-facts` 时每个 turn → 1 个 `fact`（`category` = session_id，"
        "用于把 session_id 透传到 facts metadata）。",
        "- **检索**：调用 `memory.search_episodes` / `search_facts` / `search_reflections`。"
        "reflections 层在纯检索 benchmark 不灌入（需要 LLM 抽取），返回空，不计入 fused。",
        "- **fused**：episodes + facts 合并，按 `session_id` 去重取 max score，"
        "降序取 top-K（参考 `memory.search_all`）。",
        "- **弃权题**（`answer_session_ids` 为空或 `question_id` 以 `_abs` 结尾）不计入 R@K。",
        "- **隔离**：DB/Chroma 指到 `evals/.bench_data/`，不动生产记忆库。"
        "每题之间 `reset_bench_index()` 清空三个 collection。",
        "",
        "## 参考分数（同 embedding + 纯检索）",
        "",
        "| 系统 | R@5 | 备注 |",
        "|---|---|---|",
        "| MemPalace (ChromaDB raw, all-MiniLM-L6-v2) | 96.6% | R@5 only |",
        "| Awareness Memory (Hybrid RRF, e5-small) | 96.0% | daemon 实路径 |",
        "| agentmemory (BM25+Vector, all-MiniLM-L6-v2) | 95.2% | hybrid |",
        "",
        "> 注：以上是 retrieval recall，不是 LongMemEval 官方的端到端 QA accuracy。"
        "官方 QA leaderboard（retrieve+generate+GPT-4o judge）分数普遍 60-95%。",
        "",
    ])

    # 失败样例
    misses = [r for r in stats["results"]
              if not r.get("is_abstention") and not r.get("error")
              and not r["k_hits"].get("fused", {}).get(5, False)]
    if misses:
        lines.extend(["## R@5 未命中样例（前 20）", ""])
        for r in misses[:20]:
            lines.append(f"- `{r['question_id']}` ({r['question_type']}, "
                        f"gold={r['gold_count']}, episodes={r.get('n_episodes', 0)})")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("报告已保存: %s", report_path)
    return str(report_path)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Counterpart · LongMemEval 检索 benchmark（评测会话级 R@K）"
    )
    parser.add_argument(
        "--data", required=True,
        help="LongMemEval JSON 路径（如 evals/data/longmemeval_s_cleaned.json）",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="只跑前 N 题（快速测试，如 --limit 10）",
    )
    parser.add_argument(
        "--with-facts", action="store_true",
        help="同时索引 turn 级 facts（更细粒度，但更慢）",
    )
    parser.add_argument(
        "--with-dates", action="store_true",
        help="session 文本前加日期，帮助 temporal-reasoning 题型",
    )
    parser.add_argument(
        "--k", type=int, nargs="+", default=[1, 3, 5, 10],
        help="要算的 K 值列表（默认 1 3 5 10；只算 R@5 可 --k 5）",
    )
    parser.add_argument(
        "--no-save", action="store_true", help="不保存 Markdown 报告文件",
    )
    args = parser.parse_args()

    stats = run_bench(
        data_path=args.data,
        limit=args.limit,
        with_dates=args.with_dates,
        with_facts=args.with_facts,
        k_list=args.k,
    )
    print_report(stats)
    if not args.no_save:
        save_report(stats)
