from __future__ import annotations

import html
import json
import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8765))
OFFICIAL_CASE_LIBRARY_URL = "http://rmfyalk.court.gov.cn"
CASE_LIBRARY_PATH = Path(__file__).with_name("cases.json")


LEGAL_KEYWORDS = {
    "直播带货": ["直播", "带货", "主播", "达人", "直播间", "短视频"],
    "虚假宣传": ["虚假宣传", "夸大宣传", "误导", "不实", "绝对化用语", "功效宣传"],
    "消费者权益": ["消费者", "购买", "退货", "欺诈", "三倍赔偿"],
    "产品责任": ["质量问题", "缺陷", "食品安全", "药品", "保健品", "瑕疵"],
    "网络平台责任": ["平台", "电商平台", "审核", "下架", "店铺", "入驻"],
    "广告代言": ["代言", "推荐", "证明", "广告", "背书"],
    "合同纠纷": ["合同", "订单", "价款", "违约", "退款"],
    "侵权责任": ["侵权", "损害", "损失", "过错", "因果关系"],
    "连带责任": ["连带责任", "共同责任", "共同侵权", "补充责任"],
    "明知应知": ["明知", "应知", "未核实", "审查义务", "注意义务"],
    "获利分成": ["佣金", "分成", "收益", "坑位费", "推广费", "返佣"],
    "网约车服务": ["网约车", "司机", "乘客", "接单", "派单", "行程", "平台派单"],
    "绕路": ["绕路", "偏航", "路线", "导航", "未按约定路线", "延误"],
    "误机损失": ["误机", "航班", "机票", "退改签", "赶飞机", "行程延误"],
    "运输合同": ["运输合同", "客运合同", "旅客运输", "承运人", "安全送达"],
    "违约赔偿": ["违约赔偿", "可预见损失", "扩大损失", "损失证明"],
    "健身服务": ["健身房", "健身馆", "私教", "课程", "健身服务", "会籍", "会员"],
    "预付卡": ["会员卡", "储值卡", "预付卡", "充值", "余额", "剩余课时", "预付款"],
    "闭店停业": ["闭店", "跑路", "停业", "关店", "歇业", "无法履约", "门店关闭"],
    "余额返还": ["追回", "退费", "退款", "返还", "余额返还", "解除合同"],
    "餐饮服务": ["餐厅", "饭店", "酒店", "餐饮", "包间", "宴席", "用餐", "就餐"],
    "禁止自带酒水": ["禁止自带酒水", "自带酒水", "不得自带酒水", "谢绝自带酒水", "开瓶费", "酒水服务费"],
    "格式条款": ["格式条款", "霸王条款", "店堂告示", "单方规定", "消费者选择权", "公平交易权"],
    "外卖配送": ["外卖", "骑手", "送餐", "配送", "配送员", "众包", "专送", "即时配送"],
    "交通事故": ["撞伤", "撞倒", "刮碰", "行人", "交通事故", "电动车", "非机动车", "机动车"],
    "平台用工": ["平台用工", "算法派单", "劳动关系", "劳务关系", "承揽", "雇佣", "管理控制"],
    "用人单位责任": ["用人单位责任", "雇主责任", "工作人员侵权", "执行工作任务", "职务行为", "替代责任"],
    "宠物寄养": ["宠物", "宠物店", "寄养", "托管", "看护", "猫", "狗", "走失"],
}


ISSUE_TEMPLATES = [
    ("是否构成虚假宣传", ["虚假宣传", "夸大宣传", "不实", "误导", "绝对化用语", "功效宣传"]),
    ("主播是否参与商品宣传并形成交易影响", ["主播", "直播", "带货", "推荐", "证明", "背书"]),
    ("主播是否明知或应知宣传内容不实", ["明知", "应知", "未核实", "审查义务", "注意义务"]),
    ("主播、商家、平台之间如何分配责任", ["连带责任", "平台", "商家", "责任分配", "共同侵权"]),
    ("消费者是否因宣传产生错误认识并购买", ["消费者", "购买", "误导", "错误认识", "因果关系"]),
    ("主播获利或合作模式是否影响责任认定", ["佣金", "分成", "合作", "坑位费", "推广费"]),
    ("平台是否尽到审核、提示和处置义务", ["平台", "审核", "下架", "入驻", "投诉"]),
    ("网约车司机绕路或延误是否构成违约", ["网约车", "司机", "绕路", "偏航", "延误"]),
    ("误机损失是否属于可预见且可证明的赔偿范围", ["误机", "航班", "机票", "退改签", "可预见损失"]),
    ("网约车平台是否应对司机履约行为承担责任", ["平台", "派单", "网约车", "运输合同", "承运人"]),
    ("健身房闭店是否构成根本违约", ["健身房", "闭店", "停业", "无法履约", "关店"]),
    ("会员卡余额或剩余课时能否返还", ["会员卡", "预付卡", "余额", "剩余课时", "退费", "返还"]),
    ("经营者转让门店或变更主体后谁承担退款责任", ["转让", "更名", "新经营者", "原经营者", "承接"]),
    ("格式条款或不退费约定是否有效", ["格式条款", "不退费", "霸王条款", "单方解释", "消费者"]),
    ("餐厅禁止自带酒水是否构成不公平格式条款", ["禁止自带酒水", "自带酒水", "格式条款", "霸王条款", "餐厅"]),
    ("餐饮经营者能否收取开瓶费或酒水服务费", ["开瓶费", "酒水服务费", "餐饮", "服务费"]),
    ("店堂告示是否已经合理提示且是否排除消费者主要权利", ["店堂告示", "合理提示", "消费者选择权", "公平交易权"]),
    ("骑手送餐途中撞伤行人是否属于执行工作任务", ["外卖", "骑手", "送餐", "撞伤", "执行工作任务"]),
    ("外卖平台是否对骑手侵权承担替代责任或相应责任", ["平台", "外卖", "骑手", "雇主责任", "用人单位责任", "替代责任"]),
    ("骑手与平台之间法律关系如何认定", ["平台用工", "算法派单", "劳动关系", "劳务关系", "承揽", "管理控制"]),
    ("行人人身损害赔偿与交通事故责任如何分担", ["行人", "交通事故", "人身损害", "责任分担"]),
    ("宠物寄养期间走失是否构成保管或服务违约", ["宠物", "寄养", "走失", "保管", "看护"]),
    ("宠物店是否尽到安全看护和管理义务", ["宠物店", "看护", "管理义务", "安全保障", "走失"]),
    ("宠物走失损失如何证明和计算", ["宠物", "走失", "赔偿范围", "损失证明"]),
]


QUESTION_BANK = {
    "主播": "主播是否承担责任，通常取决于其是否实际参与宣传、是否以推荐或证明方式影响交易、是否尽到合理审查义务，以及是否存在佣金、坑位费等获利安排。",
    "连带": "连带责任不是当然成立。若主播与商家共同实施误导宣传，或明知、应知商品信息不实仍作推荐证明，法院更可能支持相应连带或共同责任。",
    "为什么": "裁判逻辑一般会从行为、过错、因果关系和损害四个层面展开：宣传是否不实，用户是否因该宣传购买，主体是否有审查能力与注意义务，损失是否可归责。",
    "平台": "平台责任通常看是否履行入驻审核、广告标识、投诉处置、下架整改等义务。平台若仅提供技术服务且及时处置，责任会明显减轻。",
    "原告": "支持消费者一方时，重点组织宣传截图、直播话术、购买链路、主播收益、商品检测或官方说明，以证明误导宣传和交易决定之间的因果关系。",
    "被告": "支持主播一方时，可强调主播仅作一般展示、未作专业保证、已核验合理资料、无实际销售分成，或者消费者损失与宣传内容之间缺少因果关系。",
}


@dataclass
class Case:
    title: str
    docket: str
    court: str
    date: str
    cause: str
    side: str
    facts: str
    holding: str
    reasoning: str
    result: str
    tags: list[str]
    support_for: str
    quote: str
    domain: str = "通用"
    source: str = "本地教学案例库"


@dataclass
class ParsedInput:
    raw: str
    behaviors: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    liabilities: list[str] = field(default_factory=list)
    legal_elements: dict[str, list[str]] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    query_terms: list[str] = field(default_factory=list)
    cause: str = "消费者权益保护纠纷 / 网络服务合同相关争议"
    domain: str = "通用"


def classify_domain(text: str, tokens: list[str]) -> str:
    if "外卖" in text or "骑手" in text or "送餐" in text or "配送员" in text:
        return "外卖配送"
    if "餐厅" in text or "餐饮" in text or "自带酒水" in text or "开瓶费" in text:
        return "餐饮消费"
    if "健身房" in text or "会员卡" in text or "预付卡" in text or "闭店" in text:
        return "健身预付卡"
    if "网约车" in text or "误机" in text or "绕路" in text:
        return "网约车服务"
    if "主播" in text or "直播" in text or "带货" in text:
        return "直播电商"
    if "房租" in text or "租房" in text or "租赁" in text or "押金" in text:
        return "房屋租赁"
    if "劳动" in text or "工资" in text or "加班" in text or "辞退" in text:
        return "劳动争议"
    if "医美" in text or "医疗美容" in text or "整形" in text:
        return "医疗美容"
    if "培训" in text or "补课" in text or "教育机构" in text:
        return "教育培训"
    if "宠物" in text or "寄养" in text or "猫" in text or "狗" in text:
        return "宠物服务"
    return "通用"


def load_external_cases(fallback: list[Case]) -> list[Case]:
    if not CASE_LIBRARY_PATH.exists():
        return fallback
    try:
        records = json.loads(CASE_LIBRARY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"案例库读取失败，使用代码内置案例：{exc}")
        return fallback

    cases: list[Case] = []
    required = {"title", "docket", "court", "date", "cause", "facts", "holding", "reasoning", "result", "tags", "support_for", "quote"}
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            print(f"跳过第 {index} 条案例：不是对象")
            continue
        missing = required.difference(record)
        if missing:
            print(f"跳过第 {index} 条案例：缺少字段 {sorted(missing)}")
            continue
        cases.append(
            Case(
                title=str(record["title"]),
                docket=str(record["docket"]),
                court=str(record["court"]),
                date=str(record["date"]),
                cause=str(record["cause"]),
                side=str(record.get("side", record.get("support_for", ""))),
                facts=str(record["facts"]),
                holding=str(record["holding"]),
                reasoning=str(record["reasoning"]),
                result=str(record["result"]),
                tags=[str(tag) for tag in record.get("tags", [])],
                support_for=str(record["support_for"]),
                quote=str(record["quote"]),
                domain=str(record.get("domain", "通用")),
                source=str(record.get("source", "本地案例库")),
            )
        )
    return cases or fallback


CASES = [
    Case(
        title="教学示例一：消费者诉某直播主播、食品公司网络购物合同纠纷案",
        docket="示例案号 JX-2023-001",
        court="教学示例案例库",
        date="2023-09-18",
        cause="网络购物合同纠纷",
        side="消费者",
        facts="主播在直播间宣称涉案食品具有明显调理功效，并引导消费者通过直播链接购买。商品页面和检测资料未能证明相应功效。",
        holding="主播深度参与商品卖点介绍并获取推广收益，未对核心宣传内容尽合理审查义务，应与经营者承担相应赔偿责任。",
        reasoning="法院重点审查直播话术、主播身份、推广收益、消费者下单路径与商品真实信息之间的差距，认为宣传内容足以影响购买决定。",
        result="支持消费者部分赔偿请求，主播与商家在误导宣传范围内承担责任。",
        tags=["直播带货", "虚假宣传", "主播", "明知应知", "获利分成", "消费者权益", "连带责任"],
        support_for="消费者",
        quote="主播并非当然免责，是否担责取决于其参与程度、获利情况和审查义务履行情况。",
    ),
    Case(
        title="教学示例二：消费者诉某文化传媒公司、化妆品店产品宣传责任纠纷案",
        docket="示例案号 JX-2022-002",
        court="教学示例案例库",
        date="2022-12-06",
        cause="产品责任纠纷",
        side="消费者",
        facts="MCN机构安排达人直播推广化妆品，直播中使用绝对化用语并暗示医疗美容效果，消费者购买后认为效果与宣传不符。",
        holding="直播推广构成商业宣传，达人及其所属机构对明显夸大的功效表述负有审查和更正义务。",
        reasoning="法院认为普通消费者容易基于达人信任作出交易决定，MCN机构组织策划脚本并获得推广利益，应承担更高注意义务。",
        result="判令商家退款并赔偿，传媒公司在其参与宣传过错范围内承担补充赔偿责任。",
        tags=["直播带货", "虚假宣传", "广告代言", "MCN", "明知应知", "产品责任", "消费者权益"],
        support_for="消费者",
        quote="达人营销不应以流量信任替代事实核验。",
    ),
    Case(
        title="教学示例三：消费者诉某电商平台、保健品经营者信息网络买卖合同纠纷案",
        docket="示例案号 JX-2021-003",
        court="教学示例案例库",
        date="2021-10-22",
        cause="信息网络买卖合同纠纷",
        side="平台",
        facts="消费者主张平台应对入驻商家保健品功效虚假宣传承担连带赔偿责任，但平台在接到投诉后及时下架并提供经营者真实信息。",
        holding="平台已履行必要审核、提示和协助义务，现有证据不足以证明其参与虚假宣传或明知违法信息。",
        reasoning="平台责任应与其控制能力和过错程度相匹配，不能因平台提供交易空间而当然承担商家全部责任。",
        result="商家承担主要赔偿责任，驳回消费者要求平台连带赔偿的请求。",
        tags=["网络平台责任", "虚假宣传", "平台", "审核", "下架", "消费者权益"],
        support_for="平台或被告",
        quote="平台是否担责，应回到通知处置、审核能力和实际参与程度。",
    ),
    Case(
        title="教学示例四：消费者诉某主播网络直播购物损害赔偿纠纷案",
        docket="示例案号 JX-2024-004",
        court="教学示例案例库",
        date="2024-05-11",
        cause="网络直播购物损害赔偿纠纷",
        side="主播",
        facts="主播在直播中展示某品牌家电优惠信息，但未自行编辑产品参数，也未收取销售佣金。消费者主张参数误导导致损失。",
        holding="主播仅作一般商品展示，未作专业保证或核心性能承诺，且无证据证明其明知参数错误，不宜直接认定连带责任。",
        reasoning="法院区分普通展示与广告代言式推荐，认为消费者仍需证明主播过错与损害之间的因果关系。",
        result="商家承担退赔责任，消费者对主播的连带责任请求未获支持。",
        tags=["直播带货", "主播", "连带责任", "明知应知", "合同纠纷", "被告抗辩"],
        support_for="主播或被告",
        quote="主播责任不能脱离具体话术、收益关系和主观过错单独判断。",
    ),
    Case(
        title="教学示例五：消费者诉某珠宝直播间欺诈销售纠纷案",
        docket="示例案号 JX-2023-005",
        court="教学示例案例库",
        date="2023-11-29",
        cause="买卖合同纠纷",
        side="消费者",
        facts="直播间宣称珠宝为天然高等级材质并限时保真，主播多次以个人信誉作保证。鉴定结果显示商品等级与宣传明显不符。",
        holding="主播以个人信用对商品品质作保证，足以增强消费者信赖，应对未尽核验义务承担相应责任。",
        reasoning="法院将保真承诺、鉴定结论、直播成交链路和佣金收益作为相似要素，认定宣传行为与购买决定存在关联。",
        result="支持退货退款和惩罚性赔偿，主播与商家承担连带赔偿责任。",
        tags=["直播带货", "虚假宣传", "主播", "连带责任", "获利分成", "消费者权益", "欺诈"],
        support_for="消费者",
        quote="以个人信誉作商品品质保证，会显著提高主播注意义务。",
    ),
    Case(
        title="教学示例六：消费者诉某短视频达人广告代言责任纠纷案",
        docket="示例案号 JX-2022-006",
        court="教学示例案例库",
        date="2022-08-15",
        cause="广告责任纠纷",
        side="消费者",
        facts="短视频达人发布种草视频，称某减肥产品安全有效并附购买链接。后监管部门认定该产品广告含有违法功效宣传。",
        holding="达人以自身体验名义推荐商品，实质属于广告代言，应对未使用或未核验的推荐内容承担责任。",
        reasoning="法院强调广告代言与普通信息分享的边界，认为购买链接、佣金和商业合作标识是判断商业推广的重要事实。",
        result="判令经营者赔偿，达人在广告代言过错范围内承担连带责任。",
        tags=["广告代言", "虚假宣传", "短视频", "达人", "明知应知", "获利分成", "连带责任"],
        support_for="消费者",
        quote="种草内容一旦进入商业推广链条，即需接受广告责任规则评价。",
    ),
    Case(
        title="教学示例七：会员诉某健身房预付卡余额返还纠纷案",
        docket="示例案号 JX-2024-007",
        court="教学示例案例库",
        date="2024-04-16",
        cause="服务合同纠纷",
        side="消费者",
        facts="消费者办理健身房年卡并充值私教课程，健身房突然闭店且未提供同等替代服务，会员要求退还卡内余额和剩余课时费用。",
        holding="经营者停止提供约定健身服务，致使合同目的无法实现，消费者有权解除合同并要求返还未消费的预付款。",
        reasoning="法院重点审查闭店原因、合同履行期限、剩余服务价值、经营者是否提前通知及是否提供合理替代方案。不退费格式条款不能排除消费者依法解除合同和请求返还余额的权利。",
        result="支持会员解除合同，判令健身房返还会员卡余额及未履行私教课费用。",
        tags=["健身服务", "预付卡", "闭店停业", "余额返还", "合同纠纷", "消费者权益", "违约赔偿"],
        support_for="消费者",
        quote="预付式消费中，经营者停止履行主要服务义务的，未消费余额应依法返还。",
    ),
    Case(
        title="教学示例八：健身房转让后会员卡退费责任纠纷案",
        docket="示例案号 JX-2023-008",
        court="教学示例案例库",
        date="2023-07-21",
        cause="服务合同纠纷",
        side="消费者",
        facts="健身房将门店转让给新经营者后，原会员被告知只能按新价格折算使用，不能退还原会员卡余额。消费者起诉原经营者和新经营者。",
        holding="门店转让不能当然免除原经营者对既有会员合同的责任；新经营者实际承接会员服务的，也可能在承接范围内承担继续履行或退费责任。",
        reasoning="法院比较转让协议、会员通知、收款主体、门店招牌延续和会员数据交接情况，判断消费者是否同意债务转移及新经营者是否承接服务义务。",
        result="判令原经营者返还未消费余额，新经营者对其承诺承接的服务范围承担相应责任。",
        tags=["健身服务", "预付卡", "余额返还", "转让", "合同纠纷", "消费者权益"],
        support_for="消费者",
        quote="经营主体变化不能以内部转让安排对抗消费者的既有合同权益。",
    ),
    Case(
        title="教学示例九：会员诉健身机构私教课不退费格式条款纠纷案",
        docket="示例案号 JX-2022-009",
        court="教学示例案例库",
        date="2022-10-09",
        cause="服务合同纠纷",
        side="消费者",
        facts="会员购买大额私教课后因健身机构长期更换教练、课程安排困难而要求退费，合同载明“私教课售出概不退款”。",
        holding="经营者未稳定提供约定课程安排，构成服务履行瑕疵；“概不退款”条款若未合理提示且实质排除消费者主要权利，不能作为拒绝退费的当然依据。",
        reasoning="法院从格式条款提示说明义务、服务履行质量、剩余课程数量和双方过错程度确定退费范围。",
        result="支持退还未上私教课费用，酌情扣除已履行课程费用和合理管理成本。",
        tags=["健身服务", "预付卡", "余额返还", "格式条款", "合同纠纷", "消费者权益"],
        support_for="消费者",
        quote="预付课程的退费判断，应回到服务是否实际履行以及格式条款是否公平有效。",
    ),
]

CASES = load_external_cases(CASES)


def tokenize(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    tokens: list[str] = []
    for concept, words in LEGAL_KEYWORDS.items():
        if any(word in text for word in words):
            tokens.append(concept)
            tokens.extend([word for word in words if word in text])
    tokens.extend(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]+", text))
    return sorted(set(tokens), key=tokens.index)


def parse_case_input(text: str) -> ParsedInput:
    tokens = tokenize(text)
    parsed = ParsedInput(raw=text)
    parsed.domain = classify_domain(text, tokens)

    parsed.behaviors = [key for key in ["直播带货", "虚假宣传", "广告代言", "产品责任", "网约车服务", "绕路", "健身服务", "闭店停业", "餐饮服务", "禁止自带酒水", "外卖配送", "交通事故", "宠物寄养"] if key in tokens]
    parsed.subjects = [word for word in ["主播", "达人", "商家", "平台", "MCN", "消费者", "网约车司机", "司机", "乘客", "健身房", "会员", "餐厅", "饭店", "顾客", "外卖骑手", "骑手", "配送员", "行人"] if word in text]
    parsed.liabilities = [key for key in ["连带责任", "侵权责任", "消费者权益", "网络平台责任", "运输合同", "违约赔偿", "预付卡", "余额返还", "格式条款", "平台用工", "用人单位责任"] if key in tokens]
    if parsed.domain == "外卖配送":
        parsed.liabilities = ["侵权责任", "平台责任/用人单位责任", "交通事故责任"]

    parsed.legal_elements = {
        "行为性质": parsed.behaviors or ["网络交易宣传行为"],
        "责任主体": parsed.subjects or ["经营者", "推广者"],
        "责任类型": parsed.liabilities or ["赔偿责任", "审查义务"],
        "损害类型": [key for key in ["消费者权益", "产品责任", "合同纠纷", "误机损失", "预付卡", "余额返还", "格式条款", "交通事故"] if key in tokens] or ["交易决策受误导"],
    }
    if parsed.domain == "外卖配送":
        parsed.legal_elements = {
            "行为性质": parsed.behaviors or ["送餐履约过程中的交通侵权行为"],
            "责任主体": parsed.subjects or ["外卖骑手", "外卖平台", "受害行人"],
            "责任类型": parsed.liabilities,
            "损害类型": ["人身损害", "医疗费/误工费/护理费等损失", "交通事故损害"],
        }
    if parsed.domain == "宠物服务":
        parsed.legal_elements = {
            "行为性质": parsed.behaviors or ["宠物寄养或托管服务履行瑕疵"],
            "责任主体": ["宠物店/寄养服务提供者", "宠物主人"],
            "责任类型": ["服务合同违约责任", "保管合同责任", "过错赔偿责任"],
            "损害类型": ["宠物走失损失", "寻找费用", "合理精神利益相关损失需谨慎论证"],
        }

    issues = []
    for issue, markers in ISSUE_TEMPLATES:
        if any(marker in text or marker in tokens for marker in markers):
            issues.append(issue)
    if not issues:
        issues = ["案涉行为的法律性质如何认定", "相关主体是否存在过错及因果关系", "责任承担方式如何分配"]
    if "网约车" in text or "误机" in text or "绕路" in text:
        issues = [issue for issue in issues if not any(word in issue for word in ["主播", "商家", "直播"])]
    if "健身房" in text or "会员卡" in text or "预付卡" in text or "闭店" in text:
        issues = [issue for issue in issues if not any(word in issue for word in ["主播", "直播", "网约车", "误机"])]
    if "餐厅" in text or "餐饮" in text or "自带酒水" in text or "开瓶费" in text:
        issues = [issue for issue in issues if not any(word in issue for word in ["主播", "直播", "网约车", "误机", "健身房", "会员卡"])]
    if parsed.domain == "外卖配送":
        issues = [
            "骑手送餐途中撞伤行人是否属于执行工作任务",
            "外卖平台是否对骑手侵权承担替代责任或相应责任",
            "骑手与平台之间法律关系如何认定",
            "行人人身损害赔偿与交通事故责任如何分担",
        ]
    if parsed.domain == "宠物服务":
        issues = [
            "宠物寄养期间走失是否构成保管或服务违约",
            "宠物店是否尽到安全看护和管理义务",
            "宠物走失损失如何证明和计算",
        ]
    parsed.issues = issues[:5]

    if parsed.domain == "外卖配送":
        parsed.cause = "机动车交通事故责任纠纷 / 提供劳务者致害责任纠纷 / 网络服务平台责任纠纷"
    elif parsed.domain == "宠物服务":
        parsed.cause = "服务合同纠纷 / 保管合同纠纷 / 财产损害赔偿纠纷"
    elif "餐厅" in text or "餐饮" in text or "自带酒水" in text or "开瓶费" in text:
        parsed.cause = "餐饮服务合同纠纷 / 消费者权益保护纠纷"
    elif "健身房" in text or "会员卡" in text or "预付卡" in text or "闭店" in text:
        parsed.cause = "服务合同纠纷 / 预付式消费纠纷 / 消费者权益保护纠纷"
    elif "网约车" in text or "误机" in text or "绕路" in text:
        parsed.cause = "网络预约出租汽车服务合同纠纷 / 旅客运输合同纠纷"
    elif "平台" in text:
        parsed.cause = "网络服务合同纠纷 / 消费者权益保护纠纷"
    elif "主播" in text or "直播" in text:
        parsed.cause = "网络直播购物损害赔偿纠纷 / 网络购物合同纠纷"

    parsed.query_terms = sorted(set(tokens + parsed.behaviors + parsed.subjects + parsed.liabilities), key=(tokens + parsed.behaviors + parsed.subjects + parsed.liabilities).index)
    return parsed


def score_case(parsed: ParsedInput, case: Case) -> tuple[float, list[str], list[str]]:
    query_terms = set(parsed.query_terms)
    tag_hits = sorted(query_terms.intersection(case.tags))
    issue_hits = []
    case_text = " ".join([case.facts, case.holding, case.reasoning, " ".join(case.tags)])
    for issue in parsed.issues:
        markers = next((m for name, m in ISSUE_TEMPLATES if name == issue), [])
        if any(marker in case_text for marker in markers):
            issue_hits.append(issue)

    query_vector = set(tokenize(parsed.raw))
    case_vector = set(tokenize(case_text))
    lexical = len(query_vector.intersection(case_vector)) / max(1, len(query_vector.union(case_vector)))
    tag_score = len(tag_hits) / max(1, len(query_terms))
    issue_score = len(issue_hits) / max(1, len(parsed.issues))
    recency = (datetime.fromisoformat(case.date).year - 2020) / 6

    score = 0.45 * tag_score + 0.35 * issue_score + 0.15 * lexical + 0.05 * max(0, min(recency, 1))
    if "连带责任" in parsed.query_terms and "连带责任" in case.tags:
        score += 0.08
    if ("主播" in parsed.subjects or "直播" in parsed.raw) and "主播" in case.tags:
        score += 0.06
    return min(score, 1.0), tag_hits, issue_hits


def summarize_match(parsed: ParsedInput, case: Case, tag_hits: list[str], issue_hits: list[str]) -> dict[str, Any]:
    differences = []
    is_gym = any(term in parsed.raw for term in ["健身房", "会员卡", "预付卡", "闭店"])
    is_ride_hailing = any(term in parsed.raw for term in ["网约车", "误机", "绕路"])
    is_restaurant = any(term in parsed.raw for term in ["餐厅", "餐饮", "自带酒水", "开瓶费"])
    is_delivery = parsed.domain == "外卖配送"
    if "获利分成" in parsed.query_terms and "获利分成" not in case.tags:
        differences.append("该案未突出主播实际获利或销售分成。")
    if "平台" in parsed.subjects and "平台" not in case.tags and not is_gym and not is_delivery:
        differences.append("该案主要讨论主播或商家责任，平台责任部分较弱。")
    if "连带责任" in parsed.query_terms and "连带责任" not in case.tags:
        differences.append("该案没有直接支持连带责任，更适合用于责任边界分析。")
    if is_gym and "闭店停业" not in case.tags:
        differences.append("该案未直接涉及突然闭店，需重点比较服务无法继续履行的事实。")
    if is_gym and "预付卡" not in case.tags:
        differences.append("该案未直接涉及预付卡余额，退费计算规则参考价值较弱。")
    if is_ride_hailing and "误机损失" not in case.tags:
        differences.append("该案未直接涉及误机损失，需另找可预见损失和损失证明类案例。")
    if is_delivery and "外卖配送" not in case.tags:
        differences.append("该案未直接涉及外卖配送场景，需重点比较平台控制、派单管理和履职过程。")
    if is_delivery and "交通事故" not in case.tags:
        differences.append("该案未直接涉及交通事故责任，行人人身损害赔偿规则参考价值较弱。")
    if not differences:
        if is_gym:
            differences.append("核心事实与当前问题较接近，可直接比较闭店原因、剩余余额、服务替代方案和不退费条款。")
        elif is_ride_hailing:
            differences.append("核心事实与当前问题较接近，可直接比较路线偏离、延误原因、平台责任和误机损失证明。")
        elif is_restaurant:
            differences.append("核心事实与当前问题较接近，可直接比较店堂告示、格式条款、消费者选择权和是否变相强制消费。")
        elif is_delivery:
            differences.append("核心事实与当前问题较接近，可直接比较送餐是否属于履职过程、平台控制程度、骑手过错和行人损害。")
        else:
            differences.append("核心事实与当前问题较接近，可直接比较宣传参与程度、审查义务和责任承担。")

    claimant_markers = ["消费者", "受害", "行人", "乘客", "劳动者", "承租人", "会员"]
    angle = "可用于论证请求方主张" if any(marker in case.support_for for marker in claimant_markers) else "可用于区分或支持被告抗辩"
    if "主播" in case.support_for:
        angle = "可用于论证主播并非当然承担连带责任"

    return {
        "title": case.title,
        "docket": case.docket,
        "court": case.court,
        "date": case.date,
        "cause": case.cause,
        "domain": case.domain,
        "source": case.source,
        "score": round(score_case(parsed, case)[0] * 100),
        "similarities": [
            f"命中要素：{('、'.join(tag_hits) if tag_hits else '宣传行为、交易损害、责任主体')}",
            f"对应争议：{('；'.join(issue_hits) if issue_hits else '行为性质与责任分配')}",
        ],
        "differences": differences,
        "holding": case.holding,
        "summary": [
            f"案情概括：{case.facts}",
            f"争议焦点：{('；'.join(issue_hits) if issue_hits else '推广主体是否应对宣传内容承担责任')}。",
            f"法院观点：{case.reasoning}",
            f"裁判结果：{case.result}",
            f"可引用要旨：{case.quote}",
        ],
        "angle": angle,
        "support_for": case.support_for,
    }


def search_cases(text: str) -> dict[str, Any]:
    parsed = parse_case_input(text)
    ranked = []
    candidates = [
        case for case in CASES
        if parsed.domain == "通用" or case.domain in {parsed.domain, "通用"}
    ]
    if not candidates and parsed.domain == "通用":
        candidates = CASES
    for case in candidates:
        score, tag_hits, issue_hits = score_case(parsed, case)
        if parsed.domain != "通用" and case.domain == parsed.domain:
            score += 0.12
        ranked.append((score, case, tag_hits, issue_hits))
    ranked.sort(key=lambda item: (-item[0], item[1].date), reverse=False)
    top_score = ranked[0][0] if ranked else 0
    cards = [] if top_score < 0.22 else [summarize_match(parsed, case, tag_hits, issue_hits) for _, case, tag_hits, issue_hits in ranked[:3]]
    return {
        "parsed": {
            "cause": parsed.cause,
            "domain": parsed.domain,
            "behaviors": parsed.behaviors,
            "subjects": parsed.subjects,
            "liabilities": parsed.liabilities,
            "legal_elements": parsed.legal_elements,
            "issues": parsed.issues,
            "query_terms": parsed.query_terms,
        },
        "cards": cards,
        "local_match_notice": "" if cards else f"本地案例库暂未找到“{parsed.domain}”领域下足够相近的类案。为了避免误配，已停止硬凑 Top 3，请使用下方多源检索 Agent 扩展到法院官网、微信公众号公开内容和网页检索。",
        "study_tips": build_study_tips(parsed, cards),
    }


def build_official_search_plan(text: str) -> dict[str, Any]:
    parsed = parse_case_input(text)
    core_terms = parsed.query_terms[:]
    issue_terms = []
    for issue in parsed.issues:
        issue_terms.extend(re.findall(r"[\u4e00-\u9fff]{2,}", issue))

    search_terms = sorted(set(core_terms + issue_terms), key=(core_terms + issue_terms).index)
    if parsed.domain == "外卖配送":
        primary_query = "外卖骑手 送餐途中 撞伤行人 平台责任"
        fallback_queries = [
            "外卖骑手 交通事故 平台承担责任",
            "配送员 执行工作任务 侵权责任 平台",
            "众包骑手 劳务关系 雇主责任 交通事故",
        ]
        wechat_queries = [
            "外卖骑手撞伤行人 平台责任 案例",
            "送餐途中交通事故 平台是否赔偿",
            "众包骑手侵权 平台责任 裁判规则",
        ]
        web_queries = [
            "site:court.gov.cn 外卖骑手 撞伤行人 平台责任",
            "site:chinacourt.org 外卖骑手 交通事故 平台",
            "外卖骑手送餐途中撞伤行人 平台是否承担责任 类案",
        ]
        filters = [
            "优先选择法院官网、参考案例或能回溯到裁判文书的来源。",
            "案由可同时关注机动车交通事故责任纠纷、提供劳务者致害责任纠纷、劳动争议或网络服务平台责任。",
            "结果较多时，加入“执行工作任务”“算法派单”“众包骑手”“平台控制”。",
            "结果较少时，保留“外卖骑手 交通事故 平台责任”作为核心检索式。",
        ]
    elif "餐厅" in text or "餐饮" in text or "自带酒水" in text or "开瓶费" in text:
        primary_query = "餐厅 禁止自带酒水 格式条款 消费者权益"
        fallback_queries = [
            "禁止自带酒水 霸王条款 餐饮服务",
            "餐厅 开瓶费 酒水服务费 合法",
            "店堂告示 消费者选择权 公平交易权",
        ]
        wechat_queries = [
            "禁止自带酒水 格式条款 案例",
            "餐厅自带酒水 开瓶费 法院",
            "餐饮霸王条款 消费者权益 案例",
        ]
        web_queries = [
            "site:court.gov.cn 禁止自带酒水 格式条款",
            "site:chinacourt.org 餐厅 自带酒水 消费者权益",
            "餐厅禁止自带酒水是否合法 类案",
        ]
        filters = [
            "优先选择法院、市场监管、消协或能回溯到裁判文书的来源。",
            "案由优先筛选餐饮服务合同纠纷、消费者权益保护纠纷。",
            "结果较多时，加入“格式条款”“公平交易权”“消费者选择权”。",
            "结果较少时，保留“禁止自带酒水”或“开瓶费”作为核心检索词。",
        ]
    elif "健身房" in text or "会员卡" in text or "预付卡" in text or "闭店" in text:
        primary_query = "健身房 闭店 会员卡 余额 退费"
        fallback_queries = [
            "预付卡 健身房 闭店 返还余额",
            "健身房 私教课 不退费 格式条款",
            "预付式消费 服务合同 解除合同 退费",
        ]
        wechat_queries = [
            "健身房闭店 会员卡余额 法院",
            "预付卡退费 服务合同纠纷 案例",
            "健身房跑路 会员退费 裁判规则",
        ]
        web_queries = [
            "site:court.gov.cn 健身房 闭店 会员卡 退费",
            "site:chinacourt.org 健身房 预付卡 退费",
            "健身房闭店会员卡余额能否追回 类案",
        ]
        filters = [
            "优先选择法院、消协、市场监管或律师整理中能回溯到裁判文书的案例。",
            "案由优先筛选服务合同纠纷、预付式消费纠纷、消费者权益保护纠纷。",
            "结果较多时，在结果中继续检索“闭店”“余额返还”“私教课”“格式条款”。",
            "结果较少时，去掉“突然”等事实词，保留“健身房 预付卡 退费”。",
        ]
    elif "网约车" in text or "误机" in text or "绕路" in text:
        primary_query = "网约车 司机 绕路 误机 平台 赔偿"
        fallback_queries = [
            "网约车 平台责任 运输合同 误机损失",
            "司机绕路 行程延误 可预见损失",
            "网络预约出租汽车 服务合同 赔偿",
        ]
        wechat_queries = [
            "网约车 绕路 误机 赔偿 案例",
            "网约车平台 运输合同 误机损失",
            "司机绕路 行程延误 可预见损失",
        ]
        web_queries = [
            "site:court.gov.cn 网约车 绕路 误机 赔偿",
            "site:chinacourt.org 网约车 平台 赔偿",
            "网约车司机绕路导致误机 类案",
        ]
        filters = [
            "优先选择“参考案例”或法院官网发布案例。",
            "案由优先筛选合同、运输服务、网络服务、消费者权益相关类别。",
            "结果较多时，在结果中继续检索“平台责任”“误机损失”“可预见损失”。",
            "结果较少时，去掉过细事实词，保留“网约车 平台 赔偿”或“运输合同 延误 损失”。",
        ]
    else:
        primary_query = " ".join(search_terms[:8])
        fallback_queries = [
            " ".join(term for term in ["网约车", "绕路", "误机", "平台责任", "运输合同", "违约赔偿"] if term in search_terms or term in text),
            " ".join(term for term in ["平台", "司机", "乘客", "行程延误", "可预见损失"] if term in search_terms or term in text),
            " ".join(parsed.issues[:2]),
        ]
        wechat_queries = [
            f"{primary_query} 案例",
            f"{primary_query} 裁判规则",
            f"{primary_query} 法院",
        ]
        web_queries = [
            f"site:court.gov.cn {primary_query}",
            f"site:chinacourt.org {primary_query}",
            f"{primary_query} 类案",
        ]
        filters = [
            "优先选择“参考案例”、法院官网或能回溯到裁判文书的来源。",
            "先按案由筛选，再按争议焦点和关键事实筛选。",
            "结果较多时，加入责任主体、损害类型、裁判规则等限制词。",
            "结果较少时，删除过细事实，保留行为、主体、责任类型三类核心词。",
        ]
    fallback_queries = [query for query in fallback_queries if query.strip()]

    return {
        "official_url": OFFICIAL_CASE_LIBRARY_URL,
        "primary_query": primary_query or text,
        "fallback_queries": fallback_queries[:3],
        "wechat_queries": wechat_queries[:3],
        "web_queries": web_queries[:3],
        "cause": parsed.cause,
        "issues": parsed.issues,
        "filters": filters,
        "browser_agent_steps": [
            "打开人民法院案例库官网。",
            "将主检索式粘贴到首页检索框并检索。",
            "如果官方库结果太少，改用微信公众号公开检索或普通网页检索中的备用检索式。",
            "记录标题、案号、裁判规则、相似事实和不同事实。",
            "如果页面要求登录、验证码、关注公众号或人工确认，请由用户完成，智能体只继续整理公开可访问结果。",
        ],
        "notice": "该功能不会绕过验证码、登录、关注公众号、付费阅读或网站访问限制；引用案例时应优先核验法院官网、裁判文书或权威发布来源。",
    }


def build_study_tips(parsed: ParsedInput, cards: list[dict[str, Any]]) -> list[str]:
    if parsed.domain == "宠物服务":
        return [
            "先确认双方关系更接近保管合同还是宠物服务合同。",
            "重点核对寄养协议、交接记录、宠物健康和身份信息、门店看护规则。",
            "判断店家责任时，要看是否尽到围挡、看护、出入管理和及时寻找通知义务。",
            "损失证明可围绕购买或领养凭证、治疗和寻找费用、聊天记录及报警或寻宠记录组织。",
        ]
    if parsed.domain == "外卖配送":
        return [
            "先区分交通事故基础责任和平台是否承担替代责任两个层次。",
            "重点核对骑手是否处于接单、取餐、送餐途中，以及事故是否发生在履职过程中。",
            "判断平台责任时，要看平台是否派单、计价、考核、处罚、装备管理或对路线时效进行控制。",
            "证据上优先收集事故认定书、订单记录、配送轨迹、平台规则、骑手身份关系和伤情损失凭证。",
        ]
    if any(term in parsed.raw for term in ["餐厅", "餐饮", "自带酒水", "开瓶费"]):
        return [
            "先判断规则是协商条款还是餐厅单方设置的格式条款。",
            "重点比较该规则是否排除消费者自主选择权，或变相强制购买店内酒水。",
            "如果餐厅收取开瓶费，要进一步看是否事先明示、金额是否合理、是否对应实际服务。",
            "检索时同时使用“禁止自带酒水”“格式条款”“公平交易权”“消费者选择权”。",
        ]
    if any(term in parsed.raw for term in ["健身房", "会员卡", "预付卡", "闭店"]):
        return [
            "先确认合同主体、付款记录、剩余余额或剩余课时，再检索退费规则。",
            "重点比较闭店是否导致合同目的无法实现，以及经营者是否提供等价替代服务。",
            "遇到“不退费”条款，要分析是否属于格式条款以及是否排除消费者主要权利。",
            "同时收集门店公告、聊天记录、付款凭证和闭店现场证据，方便论证返还范围。",
        ]
    if any(term in parsed.raw for term in ["网约车", "误机", "绕路"]):
        return [
            "先区分司机绕路、平台派单、乘客自身安排三类原因。",
            "误机损失要重点证明可预见性、因果关系和实际损失金额。",
            "检索时同时保留支持平台责任和限制赔偿范围的案例。",
        ]
    tips = [
        "先用争议焦点检索，再用事实要素筛选，避免只搜零散关键词。",
        "比较主播话术、是否获利、是否核验、消费者购买链路四类事实。",
        "同时保留支持与不支持责任的案例，模拟法庭论证会更完整。",
    ]
    if "连带责任" in parsed.query_terms:
        tips.append("论证连带责任时，要特别补强共同宣传、共同获利或明知应知的证据。")
    if cards and "主播" in cards[0]["support_for"]:
        tips.append("首位案例偏向主播抗辩，可作为区分不利案例的训练素材。")
    return tips[:4]


def answer_question(question: str, context: str) -> dict[str, str]:
    merged = question + " " + context
    for key, answer in QUESTION_BANK.items():
        if key in merged:
            return {"answer": answer}
    return {
        "answer": "可以按“行为性质、主体过错、因果关系、责任范围”四步分析。先判断宣传是否足以误导消费者，再看主播或平台是否实际参与、是否获利、是否能核验，最后比较类案中的裁判要旨是否支持你的立场。"
    }


def export_markdown(payload: dict[str, Any]) -> str:
    result = search_cases(payload.get("query", ""))
    lines = ["# 类案检索速配报告", ""]
    lines.append(f"检索问题：{payload.get('query', '')}")
    lines.append(f"建议案由：{result['parsed']['cause']}")
    lines.append("")
    lines.append("## 争议焦点")
    for issue in result["parsed"]["issues"]:
        lines.append(f"- {issue}")
    lines.append("")
    lines.append("## Top 3 类案卡片")
    for idx, card in enumerate(result["cards"], 1):
        lines.append(f"### {idx}. {card['title']}")
        lines.append(f"- 案号：{card['docket']}")
        lines.append(f"- 法院/日期：{card['court']}，{card['date']}")
        lines.append(f"- 匹配度：{card['score']}%")
        lines.append(f"- 裁判要旨：{card['holding']}")
        lines.append(f"- 可借鉴角度：{card['angle']}")
        lines.append("- 学习型摘要：")
        for sentence in card["summary"]:
            lines.append(f"  - {sentence}")
        lines.append("")
    return "\n".join(lines)


INDEX_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>类案检索速配智能体</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #172033;
      --muted: #5d6a7c;
      --line: #d9e0ea;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --accent: #1d6f8f;
      --accent-2: #8a4f1d;
      --soft: #eaf5f7;
      --good: #28724f;
      --warn: #ad5a11;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      background: #ffffff;
      border-bottom: 1px solid var(--line);
      padding: 18px clamp(18px, 5vw, 52px);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }
    h1 { margin: 0; font-size: clamp(22px, 3vw, 32px); letter-spacing: 0; }
    header p { margin: 4px 0 0; color: var(--muted); font-size: 14px; }
    main {
      width: min(1280px, 100%);
      margin: 0 auto;
      padding: 22px clamp(14px, 3vw, 34px) 40px;
      display: grid;
      grid-template-columns: minmax(320px, 430px) 1fr;
      gap: 18px;
    }
    section, aside, .card, dialog {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .input-panel { padding: 18px; align-self: start; position: sticky; top: 14px; }
    label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 8px; }
    textarea {
      width: 100%;
      min-height: 168px;
      resize: vertical;
      border: 1px solid #c8d3df;
      border-radius: 8px;
      padding: 12px;
      font: inherit;
      line-height: 1.55;
      color: var(--ink);
      background: #fbfcfe;
    }
    .button-row { display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
    button {
      border: 1px solid transparent;
      border-radius: 7px;
      min-height: 38px;
      padding: 0 14px;
      font: inherit;
      cursor: pointer;
      background: #edf2f7;
      color: var(--ink);
    }
    button.primary { background: var(--accent); color: white; }
    button.ghost { border-color: var(--line); background: white; }
    button:focus-visible, textarea:focus, input:focus { outline: 3px solid #c8e6ef; outline-offset: 1px; }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .chip {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 3px 9px;
      border-radius: 999px;
      background: var(--soft);
      color: #155467;
      font-size: 12px;
      border: 1px solid #c8e3e9;
    }
    .workspace { display: grid; gap: 14px; }
    .analysis-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .mini { padding: 14px; }
    .mini h2, .results h2, .qa h2 { margin: 0 0 10px; font-size: 17px; }
    .mini dl { margin: 0; display: grid; gap: 8px; }
    .mini dt { color: var(--muted); font-size: 12px; }
    .mini dd { margin: 2px 0 0; line-height: 1.5; }
    .results { padding: 16px; }
    .cards { display: grid; gap: 12px; }
    .case-card { padding: 15px; }
    .case-head {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: start;
    }
    .case-card h3 { margin: 0; font-size: 18px; line-height: 1.35; }
    .meta { margin-top: 5px; color: var(--muted); font-size: 13px; line-height: 1.5; }
    .score {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: #f2f7e9;
      color: var(--good);
      border: 1px solid #d5e7bd;
      font-weight: 700;
    }
    .two-col { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
    .note { background: #fbfcfe; border: 1px solid #e3e8ef; border-radius: 8px; padding: 10px; line-height: 1.55; }
    .note b { color: var(--accent-2); }
    details { margin-top: 10px; }
    summary { cursor: pointer; color: var(--accent); font-weight: 650; }
    ul { padding-left: 19px; margin: 8px 0; }
    li { margin: 5px 0; line-height: 1.55; }
    mark { background: #fff1b8; padding: 0 2px; border-radius: 3px; }
    .qa { padding: 16px; display: grid; gap: 10px; }
    .qa-row { display: grid; grid-template-columns: 1fr auto; gap: 10px; }
    input {
      min-height: 38px;
      border: 1px solid #c8d3df;
      border-radius: 8px;
      padding: 0 12px;
      font: inherit;
    }
    .answer { min-height: 44px; color: var(--ink); line-height: 1.6; background: #fbfcfe; border: 1px solid #e3e8ef; border-radius: 8px; padding: 10px; }
    .empty {
      border: 1px dashed #b9c5d3;
      background: #ffffff;
      color: var(--muted);
      border-radius: 8px;
      padding: 32px;
      text-align: center;
      line-height: 1.7;
    }
    @media (max-width: 920px) {
      main { grid-template-columns: 1fr; }
      .input-panel { position: static; }
    }
    @media (max-width: 640px) {
      header { align-items: flex-start; flex-direction: column; }
      .analysis-grid, .two-col, .qa-row { grid-template-columns: 1fr; }
      .case-head { grid-template-columns: 1fr; }
      .score { width: auto; height: 38px; border-radius: 8px; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>类案检索速配智能体</h1>
      <p>把自然语言案情转换为争议焦点、法律要素和 Top 3 学习型类案卡片。内置数据为教学示例。</p>
    </div>
    <button class="ghost" id="loadExample">填入示例</button>
  </header>
  <main>
    <aside class="input-panel">
      <label for="caseInput">输入案情或检索问题</label>
      <textarea id="caseInput">直播带货虚假宣传，主播是否承担连带责任？消费者因主播推荐购买保健品，后来发现功效宣传不实，主播收取佣金但称自己只是介绍商品。</textarea>
      <div class="button-row">
        <button class="primary" id="searchBtn">速配类案</button>
        <button id="exportBtn">导出报告</button>
      </div>
      <div class="chips" id="quickChips">
        <span class="chip">虚假宣传</span>
        <span class="chip">主播责任</span>
        <span class="chip">连带责任</span>
        <span class="chip">明知应知</span>
      </div>
    </aside>
    <div class="workspace">
      <div id="analysis" class="empty">点击“速配类案”后，这里会显示案由、法律要素、争议焦点和检索关键词。</div>
      <section class="results">
        <h2>Top 3 类案卡片</h2>
        <div id="cards" class="cards">
          <div class="empty">暂无结果。</div>
        </div>
      </section>
      <section class="qa">
        <h2>多源案例检索 Agent</h2>
        <div class="button-row">
          <button id="officialPlanBtn">生成多源检索方案</button>
          <button class="ghost" id="officialOpenBtn">打开人民法院案例库</button>
          <button class="ghost" id="weixinOpenBtn">打开微信公开检索</button>
        </div>
        <div id="officialPlan" class="answer">用于把当前案情转换成法院库、微信公众号公开内容和网页检索式。遇到登录、验证码、关注或付费限制时，请人工接管。</div>
      </section>
      <section class="qa">
        <h2>智能问答与模拟法庭辅助</h2>
        <div class="qa-row">
          <input id="question" placeholder="例如：为什么主播需要承担责任？或：我代表消费者如何论证？" />
          <button id="askBtn">提问</button>
        </div>
        <div id="answer" class="answer">检索后可围绕判例摘要继续追问。</div>
      </section>
    </div>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    let lastResult = null;

    const highlight = (text, terms = []) => {
      let escaped = String(text).replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
      terms.filter(Boolean).sort((a, b) => b.length - a.length).slice(0, 12).forEach((term) => {
        const safe = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        escaped = escaped.replace(new RegExp(safe, "g"), `<mark>${term}</mark>`);
      });
      return escaped;
    };

    async function runSearch() {
      const query = $("caseInput").value.trim();
      if (!query) return;
      $("cards").innerHTML = '<div class="empty">正在解析案情并匹配类案...</div>';
      const res = await fetch("/api/search", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({query})
      });
      lastResult = await res.json();
      if (!lastResult.cards.length) {
        const planRes = await fetch("/api/official-plan", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({query})
        });
        lastResult.externalPlan = await planRes.json();
      }
      renderAnalysis(lastResult.parsed);
      renderCards(lastResult.cards, lastResult.parsed.query_terms);
    }

    function renderAnalysis(parsed) {
      const legal = parsed.legal_elements;
      $("analysis").className = "analysis-grid";
      $("analysis").innerHTML = `
        <section class="mini">
          <h2>案情解析</h2>
          <dl>
            <div><dt>建议案由</dt><dd>${parsed.cause}</dd></div>
            <div><dt>领域</dt><dd>${parsed.domain || "通用"}</dd></div>
            <div><dt>行为</dt><dd>${(parsed.behaviors.length ? parsed.behaviors : ["网络交易宣传"]).join("、")}</dd></div>
            <div><dt>主体</dt><dd>${(parsed.subjects.length ? parsed.subjects : ["经营者", "推广者"]).join("、")}</dd></div>
            <div><dt>责任类型</dt><dd>${(parsed.liabilities.length ? parsed.liabilities : ["赔偿责任"]).join("、")}</dd></div>
          </dl>
        </section>
        <section class="mini">
          <h2>争议焦点</h2>
          <ul>${parsed.issues.map((item) => `<li>${item}</li>`).join("")}</ul>
          <div class="chips">${parsed.query_terms.slice(0, 12).map((item) => `<span class="chip">${item}</span>`).join("")}</div>
        </section>
        <section class="mini">
          <h2>法律要素</h2>
          <dl>${Object.entries(legal).map(([key, val]) => `<div><dt>${key}</dt><dd>${val.join("、")}</dd></div>`).join("")}</dl>
        </section>
        <section class="mini">
          <h2>学习提示</h2>
          <ul>${lastResult.study_tips.map((item) => `<li>${item}</li>`).join("")}</ul>
        </section>
      `;
    }

    function renderCards(cards, terms) {
      if (!cards.length) {
        renderExternalSearchCards(lastResult.externalPlan, lastResult.local_match_notice);
        return;
      }
      $("cards").innerHTML = cards.map((card, index) => `
        <article class="case-card card">
          <div class="case-head">
            <div>
              <h3>${index + 1}. ${card.title}</h3>
              <div class="meta">${card.docket} · ${card.court} · ${card.date} · ${card.cause} · ${card.domain || "通用"}</div>
              <div class="meta">来源：${card.source || "本地案例库"}</div>
            </div>
            <div class="score">${card.score}%</div>
          </div>
          <div class="two-col">
            <div class="note"><b>相似点</b><ul>${card.similarities.map((item) => `<li>${highlight(item, terms)}</li>`).join("")}</ul></div>
            <div class="note"><b>差异点</b><ul>${card.differences.map((item) => `<li>${highlight(item, terms)}</li>`).join("")}</ul></div>
          </div>
          <p class="note"><b>裁判要旨：</b>${highlight(card.holding, terms)}</p>
          <p class="note"><b>可借鉴角度：</b>${card.angle}</p>
          <details>
            <summary>展开学习型摘要</summary>
            <ul>${card.summary.map((item) => `<li>${highlight(item, terms)}</li>`).join("")}</ul>
          </details>
        </article>
      `).join("");
    }

    function renderExternalSearchCards(plan, notice) {
      if (!plan) {
        $("cards").innerHTML = `<div class="empty">${notice || "暂无足够相近的本地类案。"}</div>`;
        return;
      }
      const cards = [
        {
          title: "人民法院案例库",
          source: "最高人民法院官方案例库",
          query: plan.primary_query,
          detail: "优先核验权威案例。若结果较少，使用备用检索式缩放关键词。",
          button: "打开官方库",
          url: plan.official_url
        },
        {
          title: "微信公众号公开内容",
          source: "公开文章线索",
          query: (plan.wechat_queries || []).join("；") || plan.primary_query,
          detail: "适合找法院公众号、律所文章、消协案例线索，引用前需回到权威来源核验。",
          button: "打开微信检索",
          url: "https://weixin.sogou.com/"
        },
        {
          title: "网页与法院官网检索",
          source: "法院官网/中国法院网/公开网页",
          query: (plan.web_queries || []).join("；") || plan.primary_query,
          detail: "用 site:court.gov.cn、site:chinacourt.org 等限定来源，减少泛网页噪音。",
          button: "打开网页检索",
          url: `https://www.baidu.com/s?wd=${encodeURIComponent((plan.web_queries || [plan.primary_query])[0])}`
        }
      ];
      $("cards").innerHTML = `
        <div class="empty">${notice || "本地案例库暂未找到足够相近的类案。"}</div>
        ${cards.map((card, index) => `
          <article class="case-card card">
            <div class="case-head">
              <div>
                <h3>${index + 1}. ${card.title}</h3>
                <div class="meta">来源：${card.source}</div>
              </div>
              <div class="score">检索</div>
            </div>
            <p class="note"><b>建议检索式：</b>${card.query}</p>
            <p class="note"><b>使用方式：</b>${card.detail}</p>
            <details open>
              <summary>筛选步骤</summary>
              <ul>${plan.filters.map((item) => `<li>${item}</li>`).join("")}</ul>
            </details>
            <div class="button-row">
              <button class="primary" type="button" onclick="window.open('${card.url}', '_blank', 'noopener,noreferrer')">${card.button}</button>
            </div>
          </article>
        `).join("")}
      `;
    }

    async function ask() {
      const question = $("question").value.trim();
      if (!question) return;
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({question, context: JSON.stringify(lastResult || {})})
      });
      const data = await res.json();
      $("answer").textContent = data.answer;
    }

    async function exportReport() {
      const query = $("caseInput").value.trim();
      if (!query) return;
      const res = await fetch("/api/export", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({query})
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "类案检索速配报告.md";
      a.click();
      URL.revokeObjectURL(url);
    }

    async function officialPlan() {
      const query = $("caseInput").value.trim();
      if (!query) return;
      const res = await fetch("/api/official-plan", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({query})
      });
      const data = await res.json();
      $("officialPlan").innerHTML = `
        <p><b>建议案由：</b>${data.cause}</p>
        <p><b>主检索式：</b>${data.primary_query}</p>
        <p><b>备用检索式：</b>${data.fallback_queries.join("；") || "暂无"}</p>
        <p><b>微信公众号检索式：</b>${data.wechat_queries.join("；") || "暂无"}</p>
        <p><b>网页检索式：</b>${data.web_queries.join("；") || "暂无"}</p>
        <p><b>争议焦点：</b></p>
        <ul>${data.issues.map((item) => `<li>${item}</li>`).join("")}</ul>
        <p><b>筛选步骤：</b></p>
        <ul>${data.filters.map((item) => `<li>${item}</li>`).join("")}</ul>
        <p><b>浏览器 Agent 步骤：</b></p>
        <ul>${data.browser_agent_steps.map((item) => `<li>${item}</li>`).join("")}</ul>
        <p>${data.notice}</p>
      `;
    }

    function openOfficialLibrary() {
      window.open("http://rmfyalk.court.gov.cn", "_blank", "noopener,noreferrer");
    }

    function openWeixinSearch() {
      window.open("https://weixin.sogou.com/", "_blank", "noopener,noreferrer");
    }

    $("searchBtn").addEventListener("click", runSearch);
    $("askBtn").addEventListener("click", ask);
    $("exportBtn").addEventListener("click", exportReport);
    $("officialPlanBtn").addEventListener("click", officialPlan);
    $("officialOpenBtn").addEventListener("click", openOfficialLibrary);
    $("weixinOpenBtn").addEventListener("click", openWeixinSearch);
    $("loadExample").addEventListener("click", () => {
      $("caseInput").value = "我代表消费者，想主张主播承担责任。直播间宣传某珠宝为天然高等级材质，消费者因主播保真承诺购买，鉴定后发现等级不符。主播收取佣金，商家称责任只在店铺。";
      runSearch();
    });
    runSearch();
  </script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: Any, status: int = 200) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path in ["/", "/index.html"]:
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
        else:
            self._send(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
        

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {key: value[0] for key, value in parse_qs(raw).items()}

        path = urlparse(self.path).path
        if path == "/api/search":
            query = str(payload.get("query", "")).strip()
            self._json(search_cases(query))
        elif path == "/api/official-plan":
            query = str(payload.get("query", "")).strip()
            self._json(build_official_search_plan(query))
        elif path == "/api/ask":
            self._json(answer_question(str(payload.get("question", "")), str(payload.get("context", ""))))
        elif path == "/api/export":
            content = export_markdown(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="case_match_report.md"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"类案检索速配智能体已启动：http://127.0.0.1:{PORT}")
    print(f"同一局域网设备可使用本机 IP 访问，例如：http://你的电脑IP:{PORT}")
    print("按 Ctrl+C 停止服务。")
    server.serve_forever()


if __name__ == "__main__":
    main()
