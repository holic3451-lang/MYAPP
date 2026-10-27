import re
import time
import uuid
from datetime import datetime

import streamlit as st

ITEMS_KEY = "items"
MAX_NAME_LEN = 50
MAX_QUANTITY = 999
# 같은 내용이 이 시간(초) 안에 다시 제출되면 더블클릭으로 보고 무시한다.
DUPLICATE_SUBMIT_WINDOW = 1.0


# ---------- 저장소 (PRD 6장) ----------
# 저장 방식을 바꿀 때는 이 두 함수만 수정한다.

def load_items() -> list[dict]:
    if ITEMS_KEY not in st.session_state:
        st.session_state[ITEMS_KEY] = []
    return st.session_state[ITEMS_KEY]


def save_items(items: list[dict]) -> None:
    st.session_state[ITEMS_KEY] = items


# ---------- 아이템 조작 ----------

def validate_name(name: str) -> str | None:
    """입력값에 문제가 있으면 경고 문구를, 없으면 None을 돌려준다."""
    if not name:
        return "아이템 이름을 입력해 주세요."
    if len(name) > MAX_NAME_LEN:
        return f"아이템 이름은 {MAX_NAME_LEN}자 이하로 입력해 주세요."
    return None


def add_item(name: str, quantity: int) -> None:
    items = load_items()
    items.append({
        "id": str(uuid.uuid4()),
        "name": name,
        "quantity": quantity,
        "checked": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    save_items(items)


def update_item(item_id: str, name: str, quantity: int) -> None:
    items = load_items()
    for item in items:
        if item["id"] == item_id:
            item["name"] = name
            item["quantity"] = quantity
    save_items(items)


def delete_item(item_id: str) -> None:
    save_items([item for item in load_items() if item["id"] != item_id])


def toggle_item(item_id: str) -> None:
    items = load_items()
    for item in items:
        if item["id"] == item_id:
            item["checked"] = not item["checked"]
    save_items(items)


def delete_checked_items() -> None:
    save_items([item for item in load_items() if not item["checked"]])


def delete_all_items() -> None:
    save_items([])


# ---------- 콜백 ----------
# 전체 삭제 확인창은 다른 동작을 하면 닫는다. (확인창을 띄운 채 목록이 바뀌는 것 방지)

def dismiss_clear_confirm() -> None:
    st.session_state.confirm_clear = False


def is_duplicate_submit(name: str, quantity: int) -> bool:
    last = st.session_state.last_add
    now = time.monotonic()
    st.session_state.last_add = (name, quantity, now)
    return last is not None and last[:2] == (name, quantity) and now - last[2] < DUPLICATE_SUBMIT_WINDOW


def on_add() -> None:
    dismiss_clear_confirm()
    name = st.session_state.new_name.strip()
    error = validate_name(name)
    if error:
        st.session_state.add_error = error
        return
    quantity = int(st.session_state.new_quantity)
    if not is_duplicate_submit(name, quantity):
        add_item(name, quantity)
        # 범위 밖 수량은 Streamlit이 이전 값으로 되돌려 보내므로, 실제 저장된 수량을 알려준다.
        st.session_state.toast = f"{escape_markdown(name)} x{quantity} 추가했어요"
    st.session_state.new_name = ""
    st.session_state.new_quantity = 1


def on_toggle(item_id: str) -> None:
    dismiss_clear_confirm()
    toggle_item(item_id)


def on_edit_start(item: dict) -> None:
    dismiss_clear_confirm()
    # 다른 아이템을 편집 중이었다면 그 편집은 버리고 이 아이템으로 바꾼다.
    st.session_state.editing_id = item["id"]
    st.session_state.edit_error = None
    st.session_state[f"edit_name_{item['id']}"] = item["name"]
    st.session_state[f"edit_qty_{item['id']}"] = item["quantity"]


def on_edit_save(item_id: str) -> None:
    name = st.session_state[f"edit_name_{item_id}"].strip()
    error = validate_name(name)
    if error:
        st.session_state.edit_error = error
        return
    quantity = int(st.session_state[f"edit_qty_{item_id}"])
    update_item(item_id, name, quantity)
    st.session_state.editing_id = None
    st.session_state.toast = f"{escape_markdown(name)} x{quantity}(으)로 수정했어요"


def on_edit_cancel() -> None:
    st.session_state.editing_id = None
    st.session_state.edit_error = None


def on_delete(item_id: str) -> None:
    dismiss_clear_confirm()
    if st.session_state.editing_id == item_id:
        on_edit_cancel()
    delete_item(item_id)


def on_delete_checked() -> None:
    dismiss_clear_confirm()
    if st.session_state.editing_id in {i["id"] for i in load_items() if i["checked"]}:
        on_edit_cancel()
    delete_checked_items()


def on_clear_request() -> None:
    st.session_state.confirm_clear = True


def on_clear_confirm() -> None:
    on_edit_cancel()
    delete_all_items()
    dismiss_clear_confirm()


# ---------- 화면 ----------

DANGER_COLOR = "#D64545"

CSS = f"""
<style>
/* 입력 줄과 아이템 줄은 모바일(좁은 화면)에서도 한 줄로 유지한다.
   Streamlit 기본값은 640px 미만에서 열을 세로로 쌓는다. */
[data-testid="stForm"] [data-testid="stHorizontalBlock"],
[class*="st-key-item_"] [data-testid="stHorizontalBlock"] {{
    flex-wrap: nowrap !important;
    gap: 0.5rem;
}}
[data-testid="stForm"] [data-testid="stColumn"],
[class*="st-key-item_"] [data-testid="stColumn"] {{
    min-width: 0 !important;
}}
/* 아이템 줄의 아이콘 버튼 열은 버튼 크기만큼만 차지 (수정 모드 줄은 제외) */
[class*="st-key-item_"] [data-testid="stHorizontalBlock"]:has(.stCheckbox) > [data-testid="stColumn"]:not(:first-child) {{
    flex: 0 0 auto !important;
    width: auto !important;
}}

/* 손가락으로 누르기 쉬운 크기 */
.stButton button, .stFormSubmitButton button {{
    min-height: 2.75rem;
}}
[class*="st-key-item_"] .stButton button {{
    min-width: 2.75rem;
    padding: 0 0.5rem;
}}
[class*="st-key-item_"] .stCheckbox label {{
    min-height: 2.75rem;
    align-items: center;
}}
[class*="st-key-item_"] .stCheckbox label p {{
    font-size: 1.05rem;
    word-break: break-all;
}}

/* 좁은 화면에서는 제목이 한 줄에 들어가게 */
@media (max-width: 640px) {{
    h1 {{ font-size: 1.9rem !important; }}
}}

/* 카드 간격을 조금 촘촘하게 */
[class*="st-key-item_"] {{
    padding: 0.25rem 0.75rem !important;
}}

/* 위험한 동작은 경고 색 */
.st-key-clear_all button {{
    color: {DANGER_COLOR};
    border-color: {DANGER_COLOR};
}}
.st-key-clear_all button:hover {{
    color: white;
    background-color: {DANGER_COLOR};
}}
.st-key-clear_confirm button {{
    color: white;
    background-color: {DANGER_COLOR};
    border-color: {DANGER_COLOR};
}}
</style>
"""


ZWSP = "​"


def escape_markdown(text: str) -> str:
    # 아이템 이름에 들어간 *, ~, #, $ 등이 마크다운/수식 서식으로 바뀌지 않게 한다.
    text = re.sub(r"([\\`*_{}\[\]()#+\-.!~|<>$])", r"\\\1", text)
    # :smile: 이모지 변환, :red[...] 색상 문법, URL/도메인 자동 링크는 백슬래시로 막히지 않으므로
    # ':' 뒤와 '.' 앞뒤에 보이지 않는 문자를 넣어 패턴을 끊는다. (화면 표시용이며 저장값은 그대로)
    return text.replace(":", ":" + ZWSP).replace("\\.", ZWSP + "\\." + ZWSP)


def init_state() -> None:
    st.session_state.setdefault("editing_id", None)
    st.session_state.setdefault("edit_error", None)
    st.session_state.setdefault("add_error", None)
    st.session_state.setdefault("confirm_clear", False)
    st.session_state.setdefault("last_add", None)
    st.session_state.setdefault("toast", None)


def render_progress(items: list[dict]) -> None:
    done = sum(item["checked"] for item in items)
    text = "모두 담았어요! 🎉" if done == len(items) else f"{len(items)}개 중 {done}개 완료"
    st.progress(done / len(items), text=text)


def render_add_form() -> None:
    with st.form("add_form", border=False):
        name_col, qty_col, add_col = st.columns([6, 2, 2], vertical_alignment="bottom")
        name_col.text_input(
            "아이템 이름",
            key="new_name",
            max_chars=MAX_NAME_LEN,
            placeholder="예: 우유",
        )
        qty_col.number_input("수량", min_value=1, max_value=MAX_QUANTITY, step=1, key="new_quantity")
        add_col.form_submit_button("추가", on_click=on_add, type="primary", width="stretch")

    if st.session_state.add_error:
        st.warning(st.session_state.add_error, icon="⚠️")
        st.session_state.add_error = None


def render_item(item: dict) -> None:
    item_id = item["id"]

    with st.container(border=True, key=f"item_{item_id}"):
        if st.session_state.editing_id == item_id:
            name_col, qty_col = st.columns([7, 3], vertical_alignment="bottom")
            name_col.text_input("이름 수정", key=f"edit_name_{item_id}", max_chars=MAX_NAME_LEN)
            qty_col.number_input(
                "수량", min_value=1, max_value=MAX_QUANTITY, step=1, key=f"edit_qty_{item_id}"
            )
            if st.session_state.edit_error:
                st.warning(st.session_state.edit_error, icon="⚠️")
            save_col, cancel_col = st.columns(2)
            save_col.button(
                "저장", key=f"save_{item_id}", on_click=on_edit_save, args=(item_id,),
                type="primary", width="stretch",
            )
            cancel_col.button("취소", key=f"cancel_{item_id}", on_click=on_edit_cancel, width="stretch")
            return

        label = f"{escape_markdown(item['name'])} x{item['quantity']}"
        if item["checked"]:
            label = f":gray[~~{label}~~]"

        check_col, edit_col, delete_col = st.columns([8, 1, 1], vertical_alignment="center")
        check_col.checkbox(
            label,
            value=item["checked"],
            key=f"check_{item_id}",
            on_change=on_toggle,
            args=(item_id,),
        )
        edit_col.button(
            "✏️", key=f"edit_{item_id}", on_click=on_edit_start, args=(item,), help="수정",
        )
        delete_col.button(
            "🗑️", key=f"delete_{item_id}", on_click=on_delete, args=(item_id,), help="삭제",
        )


def render_bulk_actions(items: list[dict]) -> None:
    if st.session_state.confirm_clear:
        st.warning(f"아이템 {len(items)}개를 모두 삭제할까요? 되돌릴 수 없어요.", icon="⚠️")
        yes_col, no_col = st.columns(2)
        yes_col.button("모두 삭제", key="clear_confirm", on_click=on_clear_confirm, width="stretch")
        no_col.button("취소", key="clear_cancel", on_click=dismiss_clear_confirm, width="stretch")
        return

    checked_col, all_col = st.columns(2)
    checked_col.button(
        "체크된 항목 삭제",
        on_click=on_delete_checked,
        disabled=not any(item["checked"] for item in items),
        width="stretch",
    )
    all_col.button("전체 삭제", key="clear_all", on_click=on_clear_request, width="stretch")


def main() -> None:
    st.set_page_config(page_title="쇼핑 리스트", page_icon="🛒", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    st.title("🛒 쇼핑 리스트", anchor=False)

    if st.session_state.toast:
        st.toast(st.session_state.toast, icon="✅")
        st.session_state.toast = None

    items = load_items()
    if items:
        render_progress(items)

    render_add_form()

    if not items:
        st.info("아직 아이템이 없어요. 위에서 추가해 보세요!", icon="📝")
    else:
        # 미체크 항목을 위로 (PRD 3.5 정렬). sorted는 안정 정렬이라 추가 순서가 유지된다.
        for item in sorted(items, key=lambda i: i["checked"]):
            render_item(item)

        st.divider()
        render_bulk_actions(items)

    # PRD 11장: MVP는 session_state 저장이라 새로고침하면 목록이 사라진다.
    st.caption("ℹ️ 목록은 이 브라우저 탭에만 저장돼요. 새로고침하거나 탭을 닫으면 사라져요.")


main()
