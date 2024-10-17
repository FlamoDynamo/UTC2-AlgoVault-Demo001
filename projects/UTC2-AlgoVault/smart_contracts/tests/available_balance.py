# available_balance.py

from algosdk.v2client import algod

# Hàm để kết nối với node Algorand
def connect_to_algod():
    # Thiết lập thông tin về node Algorand
    ALGOD_ADDRESS = "https://testnet-api.algonode.cloud"  # Testnet endpoint của Algonode
    ALGOD_TOKEN = ""  # Không cần API token khi sử dụng Algonode
    return algod.AlgodClient(ALGOD_TOKEN, ALGOD_ADDRESS)

# Hàm kiểm tra số dư khả dụng và số dư tối thiểu
def check_minimum_balance(address):
    client = connect_to_algod()  # Kết nối tới node cục bộ Algorand
    account_info = client.account_info(address)
    
    # Chuyển đổi số dư từ microAlgos sang Algos
    balance = account_info.get('amount') / 1e6  # Số dư thực tế
    min_balance = account_info.get('min-balance') / 1e6  # Số dư tối thiểu
    
    # In thông tin về số dư
    print(f"Số dư của tài khoản {address}: {balance} Algos")
    print(f"Số dư tối thiểu yêu cầu: {min_balance} Algos")
    print(f"Số dư khả dụng: {balance - min_balance} Algos")
    
    return balance, min_balance, balance - min_balance

check_minimum_balance("PPEURN5U5IS4OEQSV32OJHWQMIND75KB43JF7JSLZ5ZYL4TRUNB4HGVH4Q")