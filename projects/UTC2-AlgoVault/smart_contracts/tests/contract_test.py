import pytest
from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk.transaction import (
    ApplicationNoOpTxn,
    ApplicationCreateTxn,
    StateSchema,
)
from base64 import b64decode
from pyteal import *
import time

# Thiết lập thông tin về node Algorand
ALGOD_ADDRESS = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""  # Không cần API token khi sử dụng Algonode

client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)

# Ví Pera testnet của bạn
PERA_WALLET_ADDRESS = "PPEURN5U5IS4OEQSV32OJHWQMIND75KB43JF7JSLZ5ZYL4TRUNB4HGVH4Q"
PERA_WALLET_MNEMONIC = "settle patrol plunge reveal section tip resemble drift lake tissue gorilla swamp cool tomato just frown garlic shrug leg snack call jar print absent height"

# Chuyển mnemonic thành private key
def get_private_key_from_mnemonic(mnemonic_phrase):
    return mnemonic.to_private_key(mnemonic_phrase)

# Private key từ ví Pera của bạn
PERA_PRIVATE_KEY = get_private_key_from_mnemonic(PERA_WALLET_MNEMONIC)

# Hàm tiện ích tạo tài khoản Algorand
def create_algorand_account():
    private_key, address = account.generate_account()
    passphrase = mnemonic.from_private_key(private_key)
    return private_key, address, passphrase

# Hàm để biên dịch mã TEAL và giải mã từ base64
def compile_teal(client, teal_source_code):
    compile_response = client.compile(teal_source_code)
    return b64decode(compile_response["result"])  # Giải mã base64 thành chuỗi bytes

# Hàm kiểm tra trạng thái tài khoản
def check_account_status(address):
    account_info = client.account_info(address)
    print(f"Số dư của tài khoản {address}: {account_info['amount'] / 1e6} Algos")
    print(f"Số dư tối thiểu yêu cầu: {account_info['min-balance'] / 1e6} Algos")
    print(f"Địa chỉ tham gia vào ứng dụng: {account_info.get('apps-local-state', [])}")

@pytest.fixture(scope="module")
def setup_environment():
    """Thiết lập môi trường kiểm thử: sử dụng ví Pera làm ví kiểm thử"""
    user_private_key = PERA_PRIVATE_KEY
    user_address = PERA_WALLET_ADDRESS

    # Tạo tài khoản admin (hoặc sử dụng ví khác cho admin)
    admin_private_key, admin_address, admin_mnemonic = create_algorand_account()

    return {
        "user_private_key": user_private_key,
        "user_address": user_address,
        "admin_private_key": admin_private_key,
        "admin_address": admin_address,
    }

@pytest.fixture(scope="module")
def create_application(setup_environment):
    """Deploy ứng dụng smart contract lên testnet bằng file TEAL"""
    # Đọc nội dung từ file approval.teal và clear.teal
    with open("approval.teal", "r") as f:
        approval_program_teal = f.read()

    with open("clear.teal", "r") as f:
        clear_program_teal = f.read()

    # Biên dịch và giải mã các chương trình TEAL
    compiled_approval = compile_teal(client, approval_program_teal)
    compiled_clear = compile_teal(client, clear_program_teal)

    # Cấu hình phí giao dịch và tạo giao dịch
    params = client.suggested_params()
    params.flat_fee = True
    params.fee = 1000  # 0.001 ALGO (phí giao dịch cố định)
    
    on_complete = 0  # Giá trị nguyên của OnComplete.NoOp là 0
    global_schema = StateSchema(num_uints=1, num_byte_slices=1)
    local_schema = StateSchema(num_uints=0, num_byte_slices=2)

    txn = ApplicationCreateTxn(
        sender=setup_environment["admin_address"],
        sp=params,
        on_complete=on_complete,
        approval_program=compiled_approval,
        clear_program=compiled_clear,
        global_schema=global_schema,
        local_schema=local_schema,
    )

    signed_txn = txn.sign(setup_environment["admin_private_key"])
    txid = send_transaction_with_retry(signed_txn)

    # Chờ xác nhận giao dịch (đảm bảo rằng nó đã được ghi nhận)
    wait_for_confirmation(txid)

    # Lấy application id của ứng dụng đã tạo
    transaction_response = client.pending_transaction_info(txid)
    app_id = transaction_response["application-index"]
    
    # In thông tin về app_id để đảm bảo ứng dụng được tạo thành công
    print(f"Ứng dụng được tạo với Application ID: {app_id}")

    # Kiểm tra trạng thái tài khoản của admin
    check_account_status(setup_environment["admin_address"])

    return app_id

# Hàm gửi giao dịch với retry
def send_transaction_with_retry(signed_txn, retries=3):
    for i in range(retries):
        try:
            txid = client.send_transaction(signed_txn)
            return txid
        except Exception as e:
            print(f"Lỗi khi gửi giao dịch, thử lại lần {i + 1}: {e}")
            time.sleep(2)  # Chờ 2 giây trước khi thử lại
    raise Exception("Không thể gửi giao dịch sau nhiều lần thử")

# Hàm chờ xác nhận giao dịch
def wait_for_confirmation(txid):
    last_round = client.status().get('last-round')
    while True:
        txinfo = client.pending_transaction_info(txid)
        if txinfo.get('confirmed-round', 0) > 0:
            print(f"Giao dịch {txid} đã được xác nhận tại vòng {txinfo.get('confirmed-round')}")
            return
        print(f"Đang chờ xác nhận giao dịch {txid}...")
        client.status_after_block(last_round + 1)
        last_round += 1

# Thêm các test case cho store, retrieve, update và delete credentials

def test_store_credentials(setup_environment, create_application):
    """Kiểm thử lưu trữ email/username và mật khẩu đã mã hóa"""
    app_id = create_application

    # Cấu hình phí giao dịch
    params = client.suggested_params()
    params.flat_fee = True
    params.fee = 1000  # 0.001 ALGO (phí giao dịch cố định)

    username = "user@example.com"
    password = "mypassword123"  # Giả định mật khẩu đã mã hóa
    metadata = "example.com"  # Metadata cho trang web

    # Tạo giao dịch lưu trữ email/username và mật khẩu
    txn = ApplicationNoOpTxn(
        sender=setup_environment["user_address"],
        sp=params,
        index=app_id,
        app_args=[
            "store_credentials",
            "example.com",
            username,
            password,
            metadata,
        ],
    )

    signed_txn = txn.sign(setup_environment["user_private_key"])
    txid = send_transaction_with_retry(signed_txn)

    # Chờ xác nhận giao dịch
    wait_for_confirmation(txid)

    transaction_response = client.pending_transaction_info(txid)
    assert (
        transaction_response["confirmed-round"] > 0
    ), "Lưu trữ email/username và mật khẩu không thành công"

def test_retrieve_credentials(setup_environment, create_application):
    """Kiểm thử truy xuất email/username và mật khẩu đã lưu trữ"""
    app_id = create_application

    # Cấu hình phí giao dịch
    params = client.suggested_params()
    params.flat_fee = True
    params.fee = 1000  # 0.001 ALGO (phí giao dịch cố định)

    # Tạo giao dịch truy xuất email/username và mật khẩu
    txn = ApplicationNoOpTxn(
        sender=setup_environment["user_address"],
        sp=params,
        index=app_id,
        app_args=["retrieve_credentials", "example.com"],  # Truy vấn dựa trên tên website
    )

    signed_txn = txn.sign(setup_environment["user_private_key"])
    txid = send_transaction_with_retry(signed_txn)

    # Chờ xác nhận giao dịch
    wait_for_confirmation(txid)

    transaction_response = client.pending_transaction_info(txid)
    assert (
        transaction_response["confirmed-round"] > 0
    ), "Truy xuất email/username và mật khẩu không thành công"
    
    # Kiểm tra log
    logs = transaction_response.get("logs", [])
    assert len(logs) > 0, "Không có log trả về"
    
    # Giải mã log nếu cần thiết
    import base64
    decoded_log = base64.b64decode(logs[0]).decode("utf-8")
    assert "user@example.com" in decoded_log, "Email không khớp"
    assert "mypassword123" in decoded_log, "Mật khẩu không khớp"


def test_update_credentials(setup_environment, create_application):
    """Kiểm thử cập nhật email/username và mật khẩu đã mã hóa"""
    app_id = create_application

    # Cấu hình phí giao dịch
    params = client.suggested_params()
    params.flat_fee = True
    params.fee = 1000  # 0.001 ALGO (phí giao dịch cố định)

    new_password = "newpassword456"  # Mật khẩu mới được mã hóa

    # Tạo giao dịch cập nhật mật khẩu
    txn = ApplicationNoOpTxn(
        sender=setup_environment["user_address"],
        sp=params,
        index=app_id,
        app_args=[
            "update_credentials",
            "example.com",
            "user@example.com",
            new_password,
            "example.com",
        ],
    )

    signed_txn = txn.sign(setup_environment["user_private_key"])
    txid = send_transaction_with_retry(signed_txn)

    # Chờ xác nhận giao dịch
    wait_for_confirmation(txid)

    transaction_response = client.pending_transaction_info(txid)
    assert (
        transaction_response["confirmed-round"] > 0
    ), "Cập nhật mật khẩu không thành công"


def test_delete_credentials(setup_environment, create_application):
    """Kiểm thử xóa email/username và mật khẩu đã lưu trữ"""
    app_id = create_application

    # Cấu hình phí giao dịch
    params = client.suggested_params()
    params.flat_fee = True
    params.fee = 1000  # 0.001 ALGO (phí giao dịch cố định)

    # Tạo giao dịch xóa thông tin đăng nhập
    txn = ApplicationNoOpTxn(
        sender=setup_environment["user_address"],
        sp=params,
        index=app_id,
        app_args=["delete_credentials", "example.com"],
    )

    signed_txn = txn.sign(setup_environment["user_private_key"])
    txid = send_transaction_with_retry(signed_txn)

    # Chờ xác nhận giao dịch
    wait_for_confirmation(txid)

    transaction_response = client.pending_transaction_info(txid)
    assert (
        transaction_response["confirmed-round"] > 0
    ), "Xóa thông tin đăng nhập không thành công"