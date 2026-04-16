"""Curated static content for the education channel and quiz pages."""

from __future__ import annotations


EDUCATION_TRACKS = [
    {
        "slug": "deepfake",
        "label": "概念",
        "title": "Deepfake 不只是换脸，它是“合成 + 篡改 + 冒充”的统称",
        "summary": "深度伪造通常指利用生成式模型，对图像、视频、音频进行合成、替换、重定向或伪造，使人误以为内容真实发生。",
        "points": [
            "常见形式包括人脸替换、口型驱动、语音克隆、虚拟主播、假截图和伪造通话录音。",
            "它并不一定完全“从零生成”，很多案例只是把真实素材重新拼接、替换和包装。",
            "真正危险的不是技术名词，而是它和社交工程结合后会快速突破人的信任防线。",
        ],
    },
    {
        "slug": "faceswap",
        "label": "影像",
        "title": "AI 换脸为什么容易让人上当",
        "summary": "换脸内容往往借用真实视频的动作、环境和语气，只替换关键身份特征，所以第一眼更像“真的人在说话”。",
        "points": [
            "如果素材来自直播、短视频或会议录屏，观众会天然相信画面上下文是真实的。",
            "平台压缩、低清转发、二次剪辑会掩盖边缘错位、肤色漂移和嘴型不稳等瑕疵。",
            "诈骗场景里，对方通常不会给你充分时间慢慢观察画面，而是同步制造催促感。",
        ],
    },
    {
        "slug": "voice",
        "label": "音频",
        "title": "AI 换音的风险往往比换脸更隐蔽",
        "summary": "语音克隆只需要较短样本就能模仿音色、语气和停顿习惯，电话场景里更容易让人忽略异常。",
        "points": [
            "声音“像”并不等于身份真实，来电显示、头像和备注名也都可能被伪造或盗用。",
            "音频场景缺少画面佐证，人在焦虑或着急时更容易被熟人声线和紧急措辞带偏。",
            "涉钱、涉验证码、涉下载软件、涉屏幕共享的要求，都必须转入二次验证流程。",
        ],
    },
]


SCAM_SCENARIOS = [
    {
        "index": "01",
        "title": "冒充熟人求助",
        "summary": "先用熟悉头像、备注名或声音建立信任，再用“出事故了”“手机坏了”“先帮我垫一下”压缩你的判断时间。",
    },
    {
        "index": "02",
        "title": "假明星 / 假名人带货",
        "summary": "用 AI 换脸或嘴型驱动伪装成名人、医生、企业家，诱导用户点击链接、加群或投资。",
    },
    {
        "index": "03",
        "title": "假领导视频会议",
        "summary": "在群聊、视频会议、语音留言里模仿领导或客户，让财务、运营人员绕过既有审批流程。",
    },
    {
        "index": "04",
        "title": "伪造证据和舆论",
        "summary": "把深伪内容包装成“偷拍视频”“聊天截图”“突发录音”，利用传播速度先入为主。",
    },
]


SPOTTING_SIGNALS = [
    {
        "title": "画面线索",
        "items": [
            "嘴型闭合与爆破音不同步，尤其是“b / p / m”等需要明显闭嘴的发音。",
            "耳朵、发际线、眼镜边缘、首饰、下巴轮廓在转头时出现抖动、模糊或穿帮。",
            "肤色、阴影、反光方向不一致，脸部亮度与环境光源关系异常。",
            "表情和头部动作偏僵，微表情少，眨眼节奏不自然。",
        ],
    },
    {
        "title": "音频线索",
        "items": [
            "语气过于平直或突然切换，停顿像被拼接，气口和呼吸感不足。",
            "背景噪音与场景不匹配，例如说在户外却没有环境声变化。",
            "长句子前后能量分布很均匀，缺少真人说话时自然的重音和情绪波动。",
            "对方刻意避免长时间自由对话，常把你引向转账、验证码或下载操作。",
        ],
    },
    {
        "title": "行为线索",
        "items": [
            "对方要求你立刻转账、保密、不要挂断、不要联系本人或不要走正常流程。",
            "让你切到陌生平台、加入临时群、下载远程控制或屏幕共享软件。",
            "信息请求超出关系边界，例如熟人突然要身份证、银行卡、验证码、录屏。",
            "越是真实关系，越要反向确认，因为骗子正是利用“你不好意思怀疑”的心理。",
        ],
    },
]


VERIFICATION_STEPS = [
    {
        "step": "暂停",
        "title": "先把节奏抢回来",
        "detail": "一旦对方开始催钱、催码、催安装，第一动作不是配合，而是主动中断当前通话或聊天窗口。",
    },
    {
        "step": "复核",
        "title": "换一个渠道联系真人",
        "detail": "使用你自己保存过的电话号码、企业通讯录、线下联系人或面对面复核，不要回拨对方刚发来的号码。",
    },
    {
        "step": "追问",
        "title": "问只有真人才知道的问题",
        "detail": "不要问可被公开资料猜到的信息，优先问共同经历、内部流程、线下细节、约定暗号。",
    },
    {
        "step": "留痕",
        "title": "保留链接、账号、录音和截图",
        "detail": "如果已经涉及诈骗诱导，及时保留证据并向平台、学校、单位或警方求助，避免更多人被同样套路命中。",
    },
]


RESOURCE_GROUPS = [
    {
        "title": "官方科普与案例",
        "summary": "适合给频道做“知识依据”和“案例来源”，内容权威，但文章和视频不要整站搬运，建议做摘要并标注出处。",
        "links": [
            {
                "name": "FBI: Artificial Intelligence",
                "url": "https://www.fbi.gov/investigate/counterintelligence/emerging-and-advanced-technology/artificial-intelligence",
                "meta": "官方防范页，含 synthetic content / deepfake 识别提示",
            },
            {
                "name": "FBI: Senior U.S. Officials Impersonated in Malicious Messaging Campaign",
                "url": "https://www.fbi.gov/investigate/cyber/alerts/psa/senior-us-officials-impersonated-in-malicious-messaging-campaign",
                "meta": "2025-05-15，含 AI 语音仿冒和防范建议",
            },
            {
                "name": "FTC: Voice Cloning Challenge",
                "url": "https://consumer.ftc.gov/consumer-alerts/2023/11/announcing-ftcs-voice-cloning-challenge",
                "meta": "解释语音克隆风险，适合“AI 换音是什么”专题",
            },
            {
                "name": "FTC: Scammers Use Fake Emergencies To Steal Your Money",
                "url": "https://consumer.ftc.gov/articles/scammers-use-fake-emergencies-steal-your-money",
                "meta": "熟人求助 + 语音克隆诈骗场景",
            },
            {
                "name": "CISA / NSA / FBI: Deepfake Threats",
                "url": "https://www.cisa.gov/news-events/alerts/2023/09/12/nsa-fbi-and-cisa-release-cybersecurity-information-sheet-deepfake-threats",
                "meta": "适合组织、学校、企业的风险教育",
            },
            {
                "name": "中央网信办: 防范“AI换脸”诈骗，这些知识点要牢记",
                "url": "https://www.cac.gov.cn/2025-09/22/c_1760258694787465.htm",
                "meta": "2025-09-22，中文面向公众科普",
            },
            {
                "name": "中国政府网: 长沙市反电诈中心提醒 AI“换脸”软件要慎用",
                "url": "https://www.gov.cn/xinwen/2019-09/09/content_5428603.htm",
                "meta": "中文风险提示，适合做“隐私与滥用”专题",
            },
        ],
    },
    {
        "title": "可下载的视频 / 图片素材",
        "summary": "这类站点更适合拿来做频道包装、B-roll、封面和背景视频。使用前仍要二次核对单个素材页的授权说明。",
        "links": [
            {
                "name": "Pexels License",
                "url": "https://www.pexels.com/license/",
                "meta": "免费使用、可修改、通常无需署名，但不能暗示人物背书",
            },
            {
                "name": "Pexels AI Face Detection Videos",
                "url": "https://www.pexels.com/search/videos/ai%20face%20detection/",
                "meta": "适合下载检测、屏幕、科技感素材",
            },
            {
                "name": "Pixabay License Summary",
                "url": "https://pixabay.com/service/license-summary/",
                "meta": "免费、可改编，但不要原样转售或做误导性使用",
            },
            {
                "name": "Pixabay AI Faces Videos",
                "url": "https://pixabay.com/videos/search/ai%20faces/",
                "meta": "可找人脸、网络、AI 视觉背景",
            },
            {
                "name": "Wikimedia Commons Reuse Guide",
                "url": "https://commons.wikimedia.org/wiki/Special:MyLanguage/Commons:Reusing_content_outside_Wikimedia",
                "meta": "很多素材可复用，但每个文件页的署名和许可条件可能不同",
            },
            {
                "name": "Wikimedia Commons: Videos of Artificial Intelligence",
                "url": "https://commons.wikimedia.org/wiki/Category:Videos_of_artificial_intelligence",
                "meta": "适合找可注明来源的公开视频素材",
            },
            {
                "name": "FBI Protected Voices: Social Media Literacy",
                "url": "https://www.fbi.gov/video-repository/protected-voices-social-media-literacy-102319.mp4/view",
                "meta": "官方视频页提供 Video Download，适合反诈教育引用",
            },
        ],
    },
]


QUIZ_QUESTIONS = [
    {
        "level": 1,
        "question": "视频里是熟人本人，声音也很像，对方说手机摔坏了只能用这个新号联系你，并催你立刻转账。第一步最稳妥的做法是什么？",
        "options": [
            "先中断当前联系，再用你自己保存过的号码或其他渠道核实",
            "先转小额试试，对方如果继续要钱再怀疑",
            "让对方再发一段自拍视频，感觉像本人就转",
            "把聊天截图发群里问问大家",
        ],
        "answer": 0,
        "explanation": "熟人头像、声音和视频都可以被仿造。涉及金钱时，必须切换到你掌握的独立渠道复核身份，而不是在骗子控制的场景里继续判断。",
    },
    {
        "level": 1,
        "question": "下面哪一项最像 AI 换脸视频的常见破绽？",
        "options": [
            "发言内容过于流利",
            "人物转头时耳朵、下颌线或眼镜边缘出现抖动和模糊",
            "背景很清楚",
            "字幕排版很整齐",
        ],
        "answer": 1,
        "explanation": "边缘穿帮、配饰扭曲、轮廓漂移都属于典型视觉异常，尤其出现在快速转头、遮挡和压缩较强的片段里。",
    },
    {
        "level": 1,
        "question": "有人打电话自称是你领导，声音高度相似，让你立即把验证码报给他完成系统授权。哪种判断最正确？",
        "options": [
            "只要声音像，就先配合领导办事",
            "验证码不算敏感信息，可以口头报",
            "凡是验证码、密码、屏幕共享请求，都必须视为高风险并二次核验",
            "先把验证码发短信，再打电话确认",
        ],
        "answer": 2,
        "explanation": "验证码本质上就是授权凭证。AI 仿声成功率再高，也不能替代组织既有审批链和身份核验链。",
    },
    {
        "level": 1,
        "question": "关于 deepfake，下面哪种理解更准确？",
        "options": [
            "只有全程 AI 生成的视频才算 deepfake",
            "只要是美颜滤镜就算 deepfake",
            "它既可能是从零生成，也可能是在真实素材上做替换、驱动和伪造",
            "只能用于娱乐，不会影响真实决策",
        ],
        "answer": 2,
        "explanation": "深度伪造的关键在于“误导身份或事实”，不局限于从零生成，也不等同于普通滤镜。",
    },
    {
        "level": 2,
        "question": "你在短视频平台看到“知名企业家”推荐一个投资群，视频自然、口播顺畅、评论区很热闹。最需要优先核验的是什么？",
        "options": [
            "视频分辨率够不够高",
            "该账号和投资项目是否能在官方渠道被独立验证",
            "评论区有没有很多点赞",
            "口播里用了多少专业术语",
        ],
        "answer": 1,
        "explanation": "反诈判断不能只盯画面细节，更要看账号、链接、域名、认证主体和项目资质能否脱离视频本身独立成立。",
    },
    {
        "level": 2,
        "question": "下面哪项最能降低“AI 换音 + 熟人诈骗”的成功率？",
        "options": [
            "把家人的生日、学校、宠物名都公开发在社交媒体",
            "提前和家人约定仅内部知道的核验问题或暗号",
            "接到紧急电话时尽量不要挂断",
            "任何熟人来电都默认可信",
        ],
        "answer": 1,
        "explanation": "只有真人共享、难以被公开资料猜中的核验信息，才真正能提高语音仿冒场景下的识别能力。",
    },
    {
        "level": 2,
        "question": "下面哪种情况最值得警惕“上下文也被操控”了？",
        "options": [
            "对方要求你只在当前聊天窗口里确认，不要联系其他人",
            "对方能说出你的名字",
            "视频背景是办公室",
            "对方发言语速正常",
        ],
        "answer": 0,
        "explanation": "骗子最怕你离开他搭建的叙事场景。凡是阻止你交叉验证、阻止你回拨或阻止你走流程，风险都应立即上调。",
    },
    {
        "level": 2,
        "question": "如果一个视频里的嘴型、光影、动作都看不出明显问题，是否就能判定它真实？",
        "options": [
            "能，技术细节没问题就说明内容没问题",
            "不能，真实性还取决于来源、发布时间、传播链路和独立佐证",
            "能，只要是大平台发布就都是真的",
            "不能，但只有专业取证人员才能做任何判断",
        ],
        "answer": 1,
        "explanation": "深伪识别不是只看“做得像不像”，还要看“谁发的、为什么发、有没有原始出处、有没有别的可信证据支持”。",
    },
    {
        "level": 3,
        "question": "单位财务在视频会上收到“领导”指示，要求绕过原审批链先付款，理由是项目保密。最合适的处置是什么？",
        "options": [
            "金额不大就先付，避免耽误事情",
            "视频里人脸和声音都对得上，可以执行",
            "按照既定审批和回拨制度复核，不因所谓保密或紧急而跳过",
            "让同事也一起看视频，多数人觉得像就付款",
        ],
        "answer": 2,
        "explanation": "企业防深伪诈骗最关键的是流程抗压能力。制度存在的意义，就是在高压和高仿场景下替代个人直觉。",
    },
    {
        "level": 3,
        "question": "下列哪一种素材处理方式最容易在你的科普频道里引发版权风险？",
        "options": [
            "自己概括官方文章要点，并附原链接",
            "使用已核对许可条件的 Pexels / Pixabay / Commons 素材",
            "直接搬运他站完整文章、整段视频或去水印后上传到自己项目",
            "引用官方视频页并说明来源",
        ],
        "answer": 2,
        "explanation": "做教育频道也不能默认享有任意转载权。完整搬运第三方文章和视频最容易踩版权和平台规则。",
    },
    {
        "level": 3,
        "question": "如果你已经把钱转给了疑似 AI 仿冒熟人，接下来最优先的动作是什么？",
        "options": [
            "先等一等，看看对方会不会还钱",
            "继续和对方聊天，避免打草惊蛇",
            "尽快联系银行/支付平台止付，同时留存证据并报警或向平台举报",
            "把转账记录删掉，防止泄露隐私",
        ],
        "answer": 2,
        "explanation": "遇到已转账场景，时间就是止损窗口。第一优先级是止付、留痕、报警，而不是继续沉浸在骗子叙事里。",
    },
    {
        "level": 3,
        "question": "下面哪句最能代表成熟的“仿骗意识”？",
        "options": [
            "只要我眼力够好，就不会被假视频骗",
            "技术越强越没法防，只能听天由命",
            "任何看似可信的音视频，只要牵涉身份、金钱、权限，就必须做来源和流程双重验证",
            "我只防陌生人，不需要防熟人账号",
        ],
        "answer": 2,
        "explanation": "真正有效的防骗意识不是“我能看穿所有深伪”，而是建立稳定、可重复执行的验证习惯。",
    },
]


QUIZ_BADGES = [
    {
        "min_score": 0,
        "title": "警觉新手",
        "summary": "你已经知道深伪会骗人，但还需要把“暂停、换渠道、走流程”练成习惯。",
    },
    {
        "min_score": 5,
        "title": "识伪观察员",
        "summary": "你能抓到常见换脸换音线索，下一步要继续强化来源核验和组织流程意识。",
    },
    {
        "min_score": 9,
        "title": "反诈前哨",
        "summary": "你对高压诈骗场景已经有较强判断力，适合把这套方法分享给同学、家人和同事。",
    },
    {
        "min_score": 12,
        "title": "深伪侦察官",
        "summary": "你已经具备很强的仿骗意识，知道单靠眼力不够，更知道流程和交叉验证才是关键。",
    },
]
