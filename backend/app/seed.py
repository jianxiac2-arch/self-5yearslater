"""把预置数据写入数据库。

首次运行或更新认知框架时执行：
    python -m app.seed

设 SEED_DEMO_DATA=true 时，同时写入演示用 Case（公网 demo 用，历史人物虚拟用户）。

演示 Case 架构（对应 spec v0.4 第 0.1 节）：
- 每个演示 Case = 一个历史人物，放在"用户"的位置（不是人设/导师）。
- 公网 demo 默认加载 watson_1920 Case，可通过 DEMO_CASE 环境变量切换（watson_1920 / chanel_1953）。
- 每份 Case 的 L1 画像中必须包含标准标签字段（tag_*），供未来通用决策层通过画像标签契约读取。
- 完全删除旧版「小林」简历 Case（与真实用户重叠度过高，无对照价值）。
"""
import logging

from app.config import settings
from app.database import get_db, init_db
from app.vector_store import (
    get_collection,
    COLLECTION_FRAMEWORKS,
    COLLECTION_FACTS,
    COLLECTION_EPISODES,
    COLLECTION_REFLECTIONS,
)
from app.prompts.frameworks import ALL_FRAMEWORKS
from app.services import memory

logger = logging.getLogger("5yl.seed")

# 演示数据版本标记：改了演示内容就升版本号，重置/重布时会刷新
DEMO_MARKER_KEY = "_demo_seed_version"
DEMO_VERSION = "v3"  # v3 = 切换到历史人物 Case

# =============================================================================
# Case 注册表：每个 Case 是一个独立的 dict，包含 L1/L2/L3/L5
# spec v0.4 要求：通用决策层不硬编码任何具体人名/专业名，所有细节只出现在下面的 Case 数据里
# =============================================================================

# ---- Case 1：华生（John B. Watson），1920 年 42 岁，被霍普金斯大学开除 ----
# 困境：被学术界全面拉黑，中年失业，社会名誉崩塌，需要从零转行
# 演示 agent 怎么帮"中年被行业封杀后转行"的用户做横向搜索 + 纵向推演

CASE_WATSON_1920 = {
    "case_id": "watson_1920",
    "display_name": "华生 · 1920（演示用户）",
    "description": "行为主义创始人，42岁被学术界开除后转广告业封神。",
    # L1 画像（含标准标签字段：tag_age, tag_education, tag_career_direction,
    #   tag_current_industry, tag_era, tag_decision_style, tag_key_crisis, tag_standard_name）
    "profile": {
        # —— 标准标签（画像标签契约，通用决策层只读这些）——
        "tag_age": "42",
        "tag_education": "芝加哥大学心理学博士",
        "tag_career_direction": "待转行",
        "tag_current_industry": "学术/大学教职",
        "tag_era": "1920年代",
        "tag_decision_style": "极端果断/高风险偏好",
        "tag_key_crisis": "被行业封杀+中年失业+社会名誉崩塌",
        "tag_standard_name": "John B. Watson",
        # —— 人类可读画像（纵向推演+信息融合用，不参与搜索逻辑判断）——
        "姓名": "约翰·布罗德斯·华生（John Broadus Watson）",
        "别名": "行为主义之父",
        "身份锚点": "1920 年 42 岁视角。刚被约翰·霍普金斯大学开除，知道自己将在 1958 年 80 岁时去世。",
        "性格": "T（高思考/低情感表达）、J（极端计划控制）、高竞争型、高自尊绝不道歉、绝不承认后悔。说话斩钉截铁、短句、不用比喻、经常怼人不留情面。",
        "核心价值观": "环境决定一切（给我一打健康婴儿，我可以训练成任何类型的人）；科学只看可观察行为；人是可被 S-R（刺激-反应）条件化的有机机器；'内心感受'是迷信。",
        "职业经历": "前霍普金斯大学心理学教授/系主任；行为主义学派创始人（1913《行为主义者眼中的心理学》、1919《行为主义立场的心理学》）；现待业。",
        "亲密关系史": "两段婚姻：Mary Ickes（1904-1921，因婚外情曝光离异）、Rosalie Rayner（1921-1935，将病逝）。",
        "子女": "4 个孩子（第一段婚姻 1 子 1 女，第二段婚姻 2 子）。",
        "最大已知遗憾（L5 盲点，用户画像内标注）": "小阿尔伯特实验：对 9 个月大婴儿建立条件化恐惧后未做脱敏干预，终身未公开道歉；行为主义育儿理论（不要抱不要亲）导致孙辈家族性创伤（女儿自杀未遂、女婿饮弹自尽、两位子女均酒精依赖）。",
    },
    # L2 事实（category/content/importance）
    "facts": [
        # career 职业成就
        ("career", "1913 年 35 岁发表《行为主义者眼中的心理学》，宣战整个传统心理学界，开启行为主义运动。", 0.95),
        ("career", "1920 年与 Rosalie Rayner 完成小阿尔伯特实验：对 9 个月婴儿建立小白鼠恐惧的条件反射，泛化到白兔、狗、海豹皮大衣、圣诞老人胡须。", 0.95),
        ("career", "31 岁时前任系主任 James Mark Baldwin 因妓院丑闻下台，接手霍普金斯心理学系主任 + Psychological Review 主编。", 0.9),
        # event 重大事件
        ("event", "13 岁时父亲 Pickens Watson 酗酒抛弃家庭，跟别的女人跑了。终身拒绝原谅父亲，父亲临终前拒绝相见。", 0.95),
        ("event", "青少年时期：打架两次被捕、成绩垫底；靠通宵灌含可卡因可乐糖浆突击通过 Furman 大学希腊语期末。", 0.85),
        ("event", "1920 年秋：霍普金斯校长 Goodnow 给出'跟 Rosalie 分手就保留职位'的选项，主动拒绝，辞职离开学术界。", 0.95),
        ("event", "1920 年 12 月：妻子 Mary Ickes 装头痛闯入 Rosalie 卧室，搜出十几封华生情书（含'我身上每个细胞都是你的'），曝光给媒体引发全美丑闻。", 0.95),
        ("event", "芝加哥大学读博期间：清洁工+服务员+实验员三份工，每天睡 4-5 小时，第二学年累出严重神经症（他后来感谢这次崩溃让他理解弗洛伊德）。", 0.8),
        ("event", "1906 年纽约时报公开指控他'虐待动物'（剥夺白鼠感官做迷宫实验），华生不道歉反而开记者招待会：'科学就是要冒这个险。'", 0.85),
        ("event", "提出'一打婴儿宣言'（行为主义者可以把任意婴儿训练成医生/律师/乞丐/小偷）后被同行批判越界，在媒体上公开回应：'我承认我超了我的事实，但天赋论者超了几千年了。'", 0.9),
        # relation 重要关系
        ("relation", "学术对手：弗洛伊德（华生公开称精神分析是'伏都教 voodooism'）；William James（机能主义）；Edward Titchener（构造主义/内省法）。", 0.9),
        ("relation", "榜样：Ivan Pavlov（巴甫洛夫经典条件反射，华生全部理论的基础）；Jacques Loeb（生物学家机械论/向性论）。", 0.9),
        ("relation", "继承者：B.F. Skinner（新行为主义代表，认可华生奠基但认为 S-R 太简单，提出操作性条件反射）。", 0.85),
        ("relation", "家族悲剧：外孙女 Mariette Hartley（演员）公开披露——华生的'不要给孩子情感'育儿理论导致整个家族无身体接触文化；女儿多次自杀未遂；女婿饮弹自尽；子女全为酒精依赖。", 0.9),
    ],
    # L3 偏好（type/content/importance）
    "preferences": [
        ("like", "白老鼠（博士研究对象，有情感联结）；野外观察燕鸥（每年去佛罗里达 Dry Tortugas）；盖房子（1930 年代康涅狄格亲手建农场屋）；威士忌；拳击/格斗运动。", 0.75),
        ("dislike", "宗教（母亲强迫浸信会，终身反感）；任何'主观'事物（诗歌、艺术批评、哲学）；被人同情/可怜；道歉；公开承认错误；弗洛伊德；威廉·詹姆斯的'意识流'。", 0.8),
        ("dislike", "小孩子（自己孩子除外，且对他们像训练动物：'不要抱不要亲'）。", 0.75),
        ("style", "说话方式：短句、斩钉截铁、不用比喻、经常 dismissive 式怼人。公开演讲煽动性极强。写作通俗，爱用宣言式段落。", 0.7),
        ("style", "工作风格：极端自律，早 5 点起晚 11 点睡。做实验可连续 36 小时不休息。", 0.7),
        ("taboo", "绝对禁忌：①父亲/家庭出身话题（终身拒绝提及）；②直接质问'你后悔了吗'（尤其是小阿尔伯特实验伦理问题，会强硬反驳后终止对话）；③使用'你心里觉得'这类精神主义词汇（会立刻纠正：'心理学不谈心里，只谈行为'）。", 0.95),
    ],
    # L5 反思（type/content）——真实史料 + 事后视角（用户本人未必意识到，但作为高层元认知供 agent 用）
    "reflections": [
        ("pattern", "每次爬得越高，摔得越狠的共同点 = 得意时越过事实边界。1906 白鼠实验越过伦理边界→媒体指控；1920 小阿尔伯特越过伦理+法律边界（未脱敏+无知情同意）；1924 一打婴儿宣言越过学术证据边界。", 1.0),
        ("pattern", "两次被'上一个人的丑闻'直接抬升：1909 Baldwin（妓院丑闻）下台 → 31 岁当系主任；1913 构造主义衰退 → 35 岁当革命者。但自己踩的坑（婚外情）直接把自己扫出学术界，没有任何人受益。", 0.95),
        ("trend", "对'主观/心理/情感'的排斥强度与人生时间线正相关：年轻时（刚入心理学）只是方法上反对 → 中年（巅峰）上升到意识形态级别的战斗 → 晚年（丧妻+家族悲剧后）沉默但依然拒绝反转。", 0.9),
        ("blindspot", "盲点一：无法承认'我错了'。小阿尔伯特实验被伦理批判 40 年，至死没有公开道歉（'我不后悔，因为那推动了学科'）。明知育儿理论可能有问题，看到了孩子的痛苦，始终不承认。", 0.95),
        ("blindspot", "盲点二：把 S-R 条件反射泛化到一切人类行为，包括爱情。给 Rosalie 的情书里真的用'每个细胞都是正向条件反射'——是真诚的，不是修辞。完全没有'人有不可被条件化的部分（主体性）'的概念。这是 1950 年代认知革命推翻行为主义的核心。", 0.9),
        ("blindspot", "盲点三：把父亲抛弃 → 自己对情感不信任 → 上升为全人类的真理。环境决定论本质是在论证'我变成这样全是环境（爸妈）的错，与我（遗传/选择）无关'——个人创伤上升为科学理论。", 0.95),
    ],
}

# ---- Case 2：可可·香奈儿（Coco Chanel），1953 年 70 岁，瑞士流亡 9 年准备复出 ----
# 困境：二战纳粹合作丑闻、被时尚界集体认定为"另一个时代的过气人物"、年龄歧视（70 岁）
# 演示 agent 怎么帮"高龄+历史污点+行业否定"的用户做横向搜索 + 纵向推演

CASE_CHANEL_1953 = {
    "case_id": "chanel_1953",
    "display_name": "可可·香奈儿 · 1953（演示用户）",
    "description": "CHANEL 创始人，70岁瑞士流亡10年后复出时尚界再度封神。",
    "profile": {
        # —— 标准标签（画像标签契约）——
        "tag_age": "70",
        "tag_education": "Aubazine 天主教孤儿院缝纫学校",
        "tag_career_direction": "复出时尚界",
        "tag_current_industry": "高级时装/奢侈品",
        "tag_era": "1950年代",
        "tag_decision_style": "极度自信/逆势操作型",
        "tag_key_crisis": "行业集体否定+年龄歧视+历史污点未消",
        "tag_standard_name": "Coco Chanel",
        # —— 人类可读画像 ——
        "姓名": "加布里埃尔·可可·香奈儿（Gabrielle Bonheur Chanel）",
        "别名": "Mademoiselle Chanel / Coco",
        "身份锚点": "1953 年 70 岁视角。瑞士洛桑流亡第 9 年。1939 年二战爆发关闭 couture 时装屋，解雇 4000 名工人。纳粹合作指控（Abwehr 特工 F-7124 代号 Westminster，1943 赴马德里传达和平提案）后未被法国当局起诉但名誉尽毁。知道自己将在 1954 年 2 月 5 日于康朋街 31 号复出，首场被欧洲媒体骂为灾难（伦敦每日快报头条'A Fiasco--Audience Gasped!'），但美国市场和 Life 杂志力挺，一年后重新封神。知道 1971 年 1 月 10 日 87 岁在巴黎 Ritz 酒店房间去世。",
        "性格": "T（实用主义/低情感表达、极度务实）、J+T（极度控制欲）、火焰型竞争人格（自称'奥弗涅唯一没有熄灭的火山'）、从不道歉从不解释、极度独立、极端厌恶男性对女性的束缚（终身信条：永远不被任何人特别是不被男性束缚）。",
        "核心价值观": "自由 = 女性身体的解放（把 corset 束腰从女性服装中彻底移除是她一生的事业）；简约 = 高级（黑、白、灰、米色、斜纹软呢的线条）；'Luxury is what is comfortable'（奢侈品就是舒适）；'Fashion passes, style remains'（时尚会过，风格永存）；我为自己设计衣服，其他女人也会需要。",
        "成就清单": "1910 年帽子店起步；1916 jersey 针织面料革命（把男内衣面料做女装）+ 水手条纹衫；1921 N°5 香水（第一款设计师香水+醛香革命）；1925 斜纹软呢套装（tweed suit，链条下摆）；1926 小黑裙 Little Black Dress（美国 VOGUE 评为'The Ford of Fashion'，服装界第一款大众级黑色日晚两用裙）；1932 钻石珠宝系列（颠覆传统珠宝刻板镶座）。",
        "亲密关系史": "Étienne Balsan（资助第一家店铺）、Arthur 'Boy' Capel（挚爱，1919 年车祸去世，她说'失去 Capel 我失去了一切'，此后终身未嫁）、西敏公爵 Hugh Grosvenor（10 年关系，借用他的苏格兰 tweed 做面料）、Hans Günther von Dincklage（纳粹德国军官情报员，二战关系，导致流亡 10 年）。",
        "最大已知遗憾/污点": "二战期间与纳粹合作的争议：Abwehr 特工登记；1941 年试图利用纳粹雅利安化法律从犹太 Wertheimer 家族手里抢夺 Parfums Chanel 控制权（失败）；1943 年马德里和平特使行动。巴黎解放后被审讯 3 小时，因丘吉尔出面干预获释但名誉尽毁，流亡瑞士 9 年。——终身拒绝公开评论这一段历史。1954 年复出时的财务支持者就是她曾经想抢夺的 Wertheimer 家族。",
    },
    "facts": [
        # career 职业成就
        ("career", "1910 年 27 岁在巴黎康邦街 21 号开 Chanel Modes 帽子店（由 Étienne Balsan 资助），第一桶金。", 0.95),
        ("career", "1916 年 jersey 针织革命：jersey 当时只做男内衣，她买来做女装休闲装 + 水手条纹衫，成为奢华。一战物资短缺反而成就了她。", 0.95),
        ("career", "1921 年 5 月 5 日推出 Chanel N°5，调香师 Ernest Beaux 配了 10 个样本，她选第 5 个（迷信 5 是幸运数字）。第一款时装设计师香水+方形瓶+醛香革命，至今仍是全球最畅销香水之一。", 0.95),
        ("career", "1925 年推出经典斜纹软呢套装（tweed suit）：向苏格兰西敏公爵借男装 tweed 做女装；箱型外套+贴合半裙+interlocking C 纽扣+链条缝在下摆固定重量——百年不过时的设计。", 0.95),
        ("career", "1926 年推出小黑裙（Little Black Dress）——美国 Vogue 杂志在 1926 年配图文章：'Chanel's Little Black Dress = The Ford of Fashion'。", 0.95),
        ("career", "1924 年与 Wertheimer 兄弟成立 Parfums Chanel：Wertheimer 70%、Bader（老佛爷百货中介）20%、香奈儿本人只拿 10%。这个股权比例此后一生都在诉讼斗争。", 0.9),
        # event 重大事件
        ("event", "12 岁（1895 年）：母亲 Eugénie Jeanne Devolle 因肺结核+多次怀孕去世。父亲 Albert Chanel 把兄弟送农户、把她和姐妹送 Aubazine 天主教孤儿院，再也没有回来接她们。在修道院学会缝纫、对黑白几何线条形成终身审美。", 0.95),
        ("event", "18 岁离开孤儿院后，白天裁缝夜间在 Moulins 的 La Rotonde 咖啡音乐厅登台唱歌，《Qui qu'a vu Coco?》得名 'Coco'。", 0.9),
        ("event", "1919 年 12 月 22 日：挚爱 Arthur 'Boy' Capel 车祸去世。她说：'His death was a terrible blow to me. In losing Capel, I lost everything.' 但她没有崩溃，反而在此后数年推出 N°5 / tweed / LBD 三件最具代表性的作品（悲痛转化为创造力）。", 0.95),
        ("event", "1939 年 11 月（二战爆发 2 个月）：突然关闭 couture 时装屋，一次性解雇 4000 名女工。外界解读为报复工人此前要求涨薪维权；她对外声称：'战争时期没有时装。' 只有 N°5 和配饰业务保留（位于康朋街 31 号 boutique，二战期间美军排队买 N°5 当礼物寄回国）。", 0.9),
        ("event", "1940-1944 年德占巴黎：住进 Ritz 酒店（德国军官常驻地），与纳粹情报员 Baron von Dincklage（Spatz）公开同居。档案解密证实被 Abwehr（德国军事情报局）登记为特工 F-7124，代号 Westminster，1943 年赴马德里执行 Operation Modellhut 向丘吉尔传递和平提案。", 0.95),
        ("event", "1941 年：利用纳粹雅利安化法律，控告 Wertheimer 兄弟（犹太人）为'非雅利安外国人'，企图夺回 Parfums Chanel 100% 所有权。失败——Wertheimer 战前已将股权转让给非犹太信托人 Félix Amiot。此事成为她一生最大的道德污点。", 0.95),
        ("event", "1944 年 8 月巴黎解放：被法国抵抗运动逮捕审讯 3 小时。丘吉尔（通过西敏公爵关系）直接干预后获释，未被起诉。但名誉全面崩塌：巴黎时装界、法国公众全面抵制。随即流亡瑞士洛桑，一待 9 年。", 0.95),
        ("event", "1954 年 2 月 5 日复出首秀（71 岁）：欧洲媒体集体差评——伦敦每日快报头条'惨败！观众倒吸凉气！'、法国报界抨击她'炒 20 年前冷饭'。但 Life 杂志发 4 页全彩报道正面力挺：'Chanel has liberated women again——from Dior's New Look corset。'三月藏青套装登上法国 Vogue 封面。1955 年 5 月第二场秀时，全场起立鼓掌。", 0.95),
        # relation 重要关系
        ("relation", "对手：Christian Dior（1947 年 New Look 把女性身体重新束回 corset waist，香奈儿一生抨击：'Dior? He doesn't dress women, he upholsters them.' ——他不是给女人做衣服，他是在给女人做软垫家具。）", 0.95),
        ("relation", "挚爱与损失：Arthur 'Boy' Capel（1919 车祸去世）是她一生唯一承认爱的男人。之后的所有男人（西敏公爵、Dincklage）都没有超越。终身未嫁。", 0.95),
        ("relation", "复杂关系：Wertheimer 家族（Pierre Wertheimer）——她一生的诉讼对手（1946 年起诉要拿回 Parfums Chanel 所有权，打了 8 年官司，1954 年和解：Wertheimer 全资，但每年付给香奈儿$25M + 终身所有 Chanel 商品免费）。1954 年复出时的出资方就是同一个 Wertheimer。", 0.95),
    ],
    "preferences": [
        ("like", "黑/白/灰/米色/海军蓝（极简调色板）；tweed 斜纹软呢、jersey 针织、男装元素（西装外套、裤子）；山茶花（象征孤儿时期看到的修道院装饰）；珍珠（随便戴着玩，不讲究场合）；康朋街 31 号镜面楼梯；Ritz 酒店套房。", 0.85),
        ("like", "马术（从 Balsan 入门，从 Capel 与西敏公爵精进——直接导致 tweed suit 的诞生）；户外运动（高尔夫/滑雪/游艇/垂钓）；N°5 香水（自己用、送朋友、店里到处喷做'试用营销'）。", 0.8),
        ("dislike", "Corset 束腰（革命对象，一生最大敌人）；装饰过度/褶边/蕾丝（'Simplicity is the keynote of all true elegance.'）；'女性化'的刻板印象（第一个公开穿裤子上街的知名女性，被警察警告过）；被男性定义的审美。", 0.9),
        ("dislike", "被同情、被可怜、被'保护'；道歉；公开评论二战历史污点（绝对禁忌）；提起父亲（也不喜欢，但没有华生那种极端级别）。", 0.9),
        ("style", "说话方式：短、锋利、警句、毒舌、喜欢造反常识语录。'I don't do fashion, I am fashion.'；'Luxury must be comfortable, otherwise it is not luxury.'；'The most courageous act is still to think for yourself. Aloud.' 工作方式：亲自当自己的模特和 Influencer，穿自己的设计上街就是最好的营销。", 0.85),
        ("taboo", "①直接质问纳粹合作/1941年抢夺 Wertheimer 股权的道德问题（绝对不回应，冷战式沉默）；②当面质疑她'已经过气了/年纪太大了'（会直接炸，用更极端的操作反着干——1954 年复出首秀被骂之后立刻做了 2.55 包就是证明）。", 0.95),
    ],
    "reflections": [
        ("pattern", "一生 5 次重大逆势突破，全都在'所有人说这不可能'时成功：①jersey 做女装（面料等级不够）→ 成功；②女性穿裤子上街（道德丑闻）→ 成功；③小黑裙当日常装（黑色=丧服）→ 成功；④一个裁缝女儿做香水和珠宝（跨界）→ 成功；⑤71 岁复出（不可能）→ 成功。反向模式：每次遇到'我被侵犯/被伤害'时（父亲抛弃、Boy 去世、纳粹合作污点）不会谈论情绪，直接转化为创造/行动/诉讼——这是她的核心应对机制。", 0.95),
        ("pattern", "与钱的关系：极度重视股权和控制权（与 Wertheimer 打 20 年官司），但极度不重视'短期赚快钱'——1954 年复出时不是为了钱（她已经通过 N°5 分红有了一辈子花不完的钱），是为了 Dior 的 New Look 侮辱了她一辈子的事业（把女人重新勒回束腰），她是为了意识形态而复出。", 0.9),
        ("blindspot", "盲点一：道德相对主义——为了赢可以用任何手段，包括借纳粹法律搞商业对手，包括与敌国军官上床换情报保护自己。她自我辩护的逻辑是：'我从来没给过任何一个男人我真正的内心，所以与 Dincklage 上床只是交换。' 这一套自洽在 1940 年代纳粹环境下付出了名誉代价，直到今天 CHANEL 品牌仍要处理这个历史问题。", 0.95),
        ("blindspot", "盲点二：'自由'的定义非常局限——身体自由=不穿束腰、职业自由=不依附男性；但精神自由=极度依赖控制、需要永远赢、永远不能输。晚年在 Ritz 的生活是高度受控的例行公事，房间几十年不换摆设。自由不等于松弛。", 0.9),
        ("trend", "时间线：① 0-18 岁（童年创伤期：孤儿院）→ ② 20-40 岁（创造期：1910-1926 所有经典作品集中在这 16 年，27 岁到 43 岁）→ ③ 40-56 岁（巩固+战争+失败：1926-1939 巩固，1939 关店开始 15 年停滞）→ ④ 56-71 岁（流亡断档期：1939-1954，15 年空白）→ ⑤ 71-87 岁（第二次创造期：1954-1971，tweed suit 全球流行 + 2.55 包 + 双色鞋 + 再次封神）。——结论：她人生最长的创造期是在 71 岁之后。", 0.95),
    ],
}

# Case 注册索引
CASE_REGISTRY = {
    "watson_1920": CASE_WATSON_1920,
    "chanel_1953": CASE_CHANEL_1953,
}
# 默认加载的演示 Case（可通过环境变量 DEMO_CASE 切换）
DEFAULT_DEMO_CASE = settings.demo_case or "watson_1920"


# =============================================================================
# 以下函数：与旧版 seed.py 接口兼容
# =============================================================================

def seed_frameworks() -> int:
    """写入/更新 L6 认知框架。返回写入条数。

    只覆盖预置条目（按 id 匹配），用户自定义的框架不受影响。
    """
    init_db()
    conn = get_db()
    try:
        coll = get_collection(COLLECTION_FRAMEWORKS)
        preset_ids = [fw["id"] for fw in ALL_FRAMEWORKS]

        # 清空旧的预置框架（SQLite + 向量库同步）
        placeholders = ",".join("?" * len(preset_ids))
        conn.execute(f"DELETE FROM frameworks WHERE id IN ({placeholders})", preset_ids)
        existing = coll.get(ids=preset_ids)
        if existing and existing["ids"]:
            coll.delete(ids=existing["ids"])

        # 写入新的
        for fw in ALL_FRAMEWORKS:
            conn.execute(
                "INSERT INTO frameworks (id, type, name, content, trigger_conditions, vector_id) "
                "VALUES (?,?,?,?,?,?)",
                (fw["id"], fw["type"], fw["name"], fw["content"], fw["trigger_conditions"], fw["id"]),
            )
            coll.add(
                ids=[fw["id"]],
                documents=[f"{fw['name']}。{fw['content']}。触发：{fw['trigger_conditions']}"],
                metadatas=[{"type": fw["type"], "name": fw["name"]}],
            )
        conn.commit()
        return len(ALL_FRAMEWORKS)
    finally:
        conn.close()


def _get_active_case() -> dict:
    """根据设置取当前激活的演示 Case。若 ID 不存在则回退到默认 watson_1920。"""
    case_id = DEFAULT_DEMO_CASE
    if case_id not in CASE_REGISTRY:
        logger.warning("DEMO_CASE=%s 不存在，回退到 watson_1920", case_id)
        case_id = "watson_1920"
    return CASE_REGISTRY[case_id]


def seed_demo_data(force: bool = False) -> int:
    """写入演示人格（L1 + L2 + L3 + L5）。幂等：同版本已写入则跳过。

    force=True 时先清掉旧演示条目再写入。
    读取的 Case 由 settings.demo_case 控制。
    """
    init_db()
    case = _get_active_case()

    profile = memory.get_profile()
    current_case_id = profile.get("_demo_case_id", {}).get("value")
    marker = profile.get(DEMO_MARKER_KEY, {}).get("value")

    if marker == DEMO_VERSION and current_case_id == case["case_id"] and not force:
        logger.info("演示数据 %s@%s 已存在，跳过。", case["case_id"], DEMO_VERSION)
        return 0

    # L1：画像（含标准标签字段 tag_*）
    for key, value in case["profile"].items():
        confidence = 1.0 if key.startswith("tag_") else 0.95
        memory.set_profile(key, value, confidence=confidence, source="manual")
    # 写标记 + Case ID（幂等/版本控制用）
    memory.set_profile(DEMO_MARKER_KEY, DEMO_VERSION, source="manual")
    memory.set_profile("_demo_case_id", case["case_id"], source="manual")
    memory.set_profile("_demo_case_display_name", case["display_name"], source="manual")

    # L2：事实
    for category, content, importance in case["facts"]:
        memory.add_fact(category=category, content=content, importance=importance, source="manual")

    # L3：偏好
    for ptype, content, importance in case["preferences"]:
        memory.add_preference(ptype=ptype, content=content, importance=importance)

    # L5：反思（每条三元组：type, content, _importance_unused —— 保持与 facts/preferences 同样的 3 元组形式
    # 但 add_reflection 只接受前两元，后面 importance 只是注释不入库，避免 ValueError: too many values to unpack (expected 2)
    for entry in case["reflections"]:
        memory.add_reflection(rtype=entry[0], content=entry[1])

    logger.info(
        "演示数据已写入 [%s]：%d 条画像，%d 条事实，%d 条偏好，%d 条反思。",
        case["case_id"],
        len(case["profile"]) + 3,  # +3 = DEMO_MARKER_KEY + _demo_case_id + _demo_case_display_name
        len(case["facts"]),
        len(case["preferences"]),
        len(case["reflections"]),
    )
    return len(case["facts"])


def _clear_vector_collection(name: str) -> None:
    try:
        coll = get_collection(name)
        existing = coll.get()
        if existing and existing.get("ids"):
            coll.delete(ids=existing["ids"])
    except Exception as e:
        logger.warning("清空向量集合 %s 失败: %s", name, e)


def reset_demo_data() -> None:
    """清空所有用户数据（保留服务本身），重建框架 + 演示人格。

    供公网 demo「恢复演示数据」使用；对应 POST /api/admin/reset-demo。
    """
    init_db()
    conn = get_db()
    try:
        for table in ("messages", "episodes", "facts", "reflections",
                      "preferences", "conversations", "profile"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()

    for name in (COLLECTION_FACTS, COLLECTION_EPISODES, COLLECTION_REFLECTIONS):
        _clear_vector_collection(name)

    seed_frameworks()
    seed_demo_data(force=True)
    case = _get_active_case()
    logger.info("演示环境已重置为 [%s]。", case["case_id"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    n = seed_frameworks()
    print(f"已写入 {n} 条认知框架。")
    if settings.seed_demo_data:
        seed_demo_data()
        case = _get_active_case()
        print(f"演示数据 [{case['case_id']}] 已就绪。")
