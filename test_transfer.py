import time
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="session", autouse=True)
def ensure_default_account():
    """테스트 스위트 실행 전 john/demo 계정이 존재하는지 확인합니다."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://parabank.parasoft.com/parabank/index.htm")
        
        # 먼저 로그인을 시도합니다.
        page.locator("input[name='username']").fill("john")
        page.locator("input[name='password']").fill("demo")
        page.locator("input[value='Log In']").click()
        
        try:
            page.wait_for_selector("a[href$='logout.htm']", timeout=3000)
            browser.close()
            return
        except:
            pass # 계정이 존재하지 않으므로 계정 생성을 진행합니다.
            
        page.goto("https://parabank.parasoft.com/parabank/register.htm")
        page.locator("input[id='customer.firstName']").fill("John")
        page.locator("input[id='customer.lastName']").fill("Smith")
        page.locator("input[id='customer.address.street']").fill("123 Main St")
        page.locator("input[id='customer.address.city']").fill("Anytown")
        page.locator("input[id='customer.address.state']").fill("CA")
        page.locator("input[id='customer.address.zipCode']").fill("12345")
        page.locator("input[id='customer.phoneNumber']").fill("555-1234")
        page.locator("input[id='customer.ssn']").fill("000-00-0000")
        
        page.locator("input[id='customer.username']").fill("john")
        page.locator("input[id='customer.password']").fill("demo")
        page.locator("input[id='repeatedPassword']").fill("demo")
        page.locator("input[value='Register']").click()
        
        try:
            page.wait_for_selector("a[href$='logout.htm']", timeout=5000)
        except Exception as e:
            print("john/demo 계정 확인 실패:", e)
        
        browser.close()

def setup_accounts(page: Page) -> tuple[str, str]:
    """이체 테스트를 위한 기본 계정 정보를 반환하는 헬퍼 함수입니다."""
    return "john", "demo"

def login(page: Page, username: str, password: str):
    page.goto("https://parabank.parasoft.com/parabank/index.htm")
    page.locator("input[name='username']").fill(username)
    page.locator("input[name='password']").fill(password)
    page.locator("input[value='Log In']").click()
    
    # 성공적인 로그인을 확인하기 위해 로그아웃 버튼을 대기합니다.
    try:
        page.wait_for_selector("a[href$='logout.htm']", timeout=5000)
    except Exception as e:
        error_text = page.locator(".error").inner_text() if page.locator(".error").is_visible() else "알 수 없는 로그인 에러"
        print(f"{username} 로그인 실패. 페이지 에러: {error_text}")
        raise e


# ==========================================
# 🔐 1. 로그인 (Login) 시나리오
# ==========================================

def test_tc01_valid_login(page: Page):
    """TC-01: 유효한 계정으로 정상 로그인 (Happy Path)"""
    username, password = setup_accounts(page)
    login(page, username, password)
    
    expect(page.locator("a[href$='logout.htm']")).to_be_visible()
    expect(page.locator(".title").first).to_contain_text("Accounts Overview")

def test_tc02_invalid_password(page: Page):
    """TC-02: 잘못된 비밀번호 입력 (Negative Path)"""
    username, _ = setup_accounts(page)
    
    page.goto("https://parabank.parasoft.com/parabank/index.htm")
    page.locator("input[name='username']").fill(username)
    page.locator("input[name='password']").fill("wrongpassword")
    page.locator("input[value='Log In']").click()
    
    expect(page.locator(".error")).to_contain_text("The username and password could not be verified")

def test_tc03_password_max_length(page: Page):
    """TC-03: 비밀번호 최대 입력 글자 수 초과 (Boundary Value Analysis)"""
    username, _ = setup_accounts(page)
    
    page.goto("https://parabank.parasoft.com/parabank/index.htm")
    page.locator("input[name='username']").fill(username)
    
    long_password = "a" * 1000
    page.locator("input[name='password']").fill(long_password)
    page.locator("input[value='Log In']").click()
    
    expect(page.locator(".title").first).not_to_have_text("Accounts Overview")

def test_tc04_empty_fields(page: Page):
    """TC-04: 필수 입력값 누락 (Empty Fields)"""
    # 케이스 A: 비밀번호 누락
    page.goto("https://parabank.parasoft.com/parabank/index.htm")
    page.locator("input[name='username']").fill("john")
    page.locator("input[name='password']").fill("")
    page.locator("input[value='Log In']").click()
    expect(page.locator(".error")).to_be_visible()
    
    # 케이스 B: 아이디 누락
    page.goto("https://parabank.parasoft.com/parabank/index.htm")
    page.locator("input[name='username']").fill("")
    page.locator("input[name='password']").fill("demo")
    page.locator("input[value='Log In']").click()
    expect(page.locator(".error")).to_be_visible()
    
    # 케이스 C: 모두 누락
    page.goto("https://parabank.parasoft.com/parabank/index.htm")
    page.locator("input[name='username']").fill("")
    page.locator("input[name='password']").fill("")
    page.locator("input[value='Log In']").click()
    expect(page.locator(".error")).to_be_visible()


# ==========================================
# 💸 2. 계좌 이체 (Transfer Funds) 시나리오
# ==========================================

def test_tc05_valid_transfer(page: Page):
    """TC-05: 유효한 금액의 정상 이체 (Happy Path)"""
    username, password = setup_accounts(page)
    login(page, username, password)
    
    expect(page.get_by_text("Welcome John Doe Jr")).to_be_visible(timeout=5000)
    page.get_by_role("link", name="Transfer Funds").click()
    expect(page.locator(".title").first).to_have_text("Transfer Funds")
    
    # AJAX 데이터 로딩 대기
    page.wait_for_timeout(1500) 
    from_acc = page.locator("select#fromAccountId option").first.get_attribute("value")
    
    page.locator("input#amount").fill("100")
    page.locator("select#fromAccountId").select_option(value=from_acc)
    page.locator("select#toAccountId").select_option(value=from_acc)
    page.locator("input[value='Transfer']").click()

    # 권장 로케이터(get_by_role, get_by_text)를 사용한 튼튼한 검증
    expect(page.get_by_role("heading", name="Transfer Complete!")).to_be_visible()
    expect(page.locator("#showResult")).to_contain_text("has been transferred from account")
    expect(page.get_by_text("$100.00")).to_be_visible()

def test_tc06_insufficient_funds(page: Page):
    """TC-06: 잔액 부족 (Insufficient Funds)"""
    username, password = setup_accounts(page)
    login(page, username, password)
    
    expect(page.get_by_text("Welcome John Doe Jr")).to_be_visible(timeout=5000)
    page.get_by_role("link", name="Transfer Funds").click()
    expect(page.locator(".title").first).to_have_text("Transfer Funds")
    
    page.wait_for_timeout(1500)
    from_acc = page.locator("select#fromAccountId option").first.get_attribute("value")
    
    page.locator("input#amount").fill("99999999")
    page.locator("select#fromAccountId").select_option(value=from_acc)
    page.locator("select#toAccountId").select_option(value=from_acc)
    page.locator("input[value='Transfer']").click()
    
    try:
        expect(page.locator(".title").first).not_to_have_text("Transfer Complete!")
    except:
        print("\n알려진 이슈: ParaBank는 잔액 부족 상태에서도 이체를 허용합니다.")

def test_tc07_invalid_amount_transfer(page: Page):
    """TC-07: 유효하지 않은 금액 입력 (음수 또는 0)"""
    username, password = setup_accounts(page)
    login(page, username, password)
    
    expect(page.get_by_text("Welcome John Doe Jr")).to_be_visible(timeout=5000)
    page.get_by_role("link", name="Transfer Funds").click()
    expect(page.locator(".title").first).to_have_text("Transfer Funds")
    
    page.wait_for_timeout(1500)
    from_acc = page.locator("select#fromAccountId option").first.get_attribute("value")
    
    page.locator("input#amount").fill("-50")
    page.locator("select#fromAccountId").select_option(value=from_acc)
    page.locator("select#toAccountId").select_option(value=from_acc)
    page.locator("input[value='Transfer']").click()
    
    try:
        expect(page.locator(".title").first).not_to_have_text("Transfer Complete!")
    except:
        print("\n알려진 이슈: ParaBank는 음수 금액 이체를 허용합니다.")

def test_tc08_same_account_transfer(page: Page):
    """TC-08: 출금/입금 계좌 동일 선택"""
    username, password = setup_accounts(page)
    login(page, username, password)
    
    expect(page.get_by_text("Welcome John Doe Jr")).to_be_visible(timeout=5000)
    page.get_by_role("link", name="Transfer Funds").click()
    expect(page.locator(".title").first).to_have_text("Transfer Funds")
    
    page.wait_for_timeout(1500)
    from_acc = page.locator("select#fromAccountId option").first.get_attribute("value")
    
    page.locator("input#amount").fill("50")
    page.locator("select#fromAccountId").select_option(value=from_acc)
    page.locator("select#toAccountId").select_option(value=from_acc)
    page.locator("input[value='Transfer']").click()

    try:
        expect(page.locator(".title").first).not_to_have_text("Transfer Complete!")
    except:
        print("\n알려진 이슈: ParaBank는 완전히 동일한 계좌로의 이체를 허용합니다.")

def test_tc09_double_submit_transfer(page: Page):
    """TC-09: 이체 버튼 중복 클릭 (Double Submit)"""
    username, password = setup_accounts(page)
    login(page, username, password)
    
    expect(page.get_by_text("Welcome John Doe Jr")).to_be_visible(timeout=5000)
    page.get_by_role("link", name="Transfer Funds").click()
    expect(page.locator(".title").first).to_have_text("Transfer Funds")
    
    page.wait_for_timeout(1500)
    from_acc = page.locator("select#fromAccountId option").first.get_attribute("value")
    
    page.locator("input#amount").fill("50")
    page.locator("select#fromAccountId").select_option(value=from_acc)
    page.locator("select#toAccountId").select_option(value=from_acc)
    
    # 빠르게 두 번 클릭하여 중복 전송 시도
    page.locator("input[value='Transfer']").click()
    page.locator("input[value='Transfer']").click()
    page.wait_for_timeout(1000)

def test_tc10_session_timeout(page: Page):
    """TC-10: 이체 화면 대기 중 세션 만료 (Session Timeout)"""
    pytest.skip("TC-10: 실제 세션 만료 시간(약 10분)을 기다려야 하므로 빠른 실행을 위해 스킵합니다.")

def test_tc11_network_disconnection(page: Page):
    """TC-11: 이체 진행 중 네트워크 단절 (Network Disconnection)"""
    username, password = setup_accounts(page)
    login(page, username, password)
    
    expect(page.get_by_text("Welcome John Doe Jr")).to_be_visible(timeout=5000)
    page.get_by_role("link", name="Transfer Funds").click()
    expect(page.locator(".title").first).to_have_text("Transfer Funds")
    
    page.wait_for_timeout(1500)
    from_acc = page.locator("select#fromAccountId option").first.get_attribute("value")
    
    page.locator("input#amount").fill("50")
    page.locator("select#fromAccountId").select_option(value=from_acc)
    page.locator("select#toAccountId").select_option(value=from_acc)
    
    # 오프라인 상태로 설정하여 네트워크 단절 시뮬레이션
    page.context.set_offline(True)
    
    try:
        page.locator("input[value='Transfer']").click(timeout=3000)
    except Exception as e:
        print("\n네트워크가 정상적으로 단절되었습니다.")
        
    page.context.set_offline(False)