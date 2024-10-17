from pyteal import *

def approval_program():
    # Các key lưu trữ
    PASSWORD_KEY_PREFIX = Bytes("pw_")  # Prefix lưu mật khẩu mã hóa
    USERNAME_KEY_PREFIX = Bytes("un_")  # Prefix lưu email/username
    METADATA_KEY_PREFIX = Bytes("meta_")  # Prefix lưu metadata (website, ghi chú)
    VERSION_KEY_PREFIX = Bytes("ver_")  # Prefix lưu phiên bản mật khẩu
    OWNER_KEY = Bytes("owner")  # Key lưu chủ sở hữu ví

    # Chức năng tạo tài khoản
    on_register = Seq([
        App.globalPut(OWNER_KEY, Txn.sender()),
        Approve()
    ])

    # Chức năng lưu trữ email/username và mật khẩu
    website_key = Txn.application_args[1]
    password_key = Concat(PASSWORD_KEY_PREFIX, website_key)  # Mã trang web cho mật khẩu
    username_key = Concat(USERNAME_KEY_PREFIX, website_key)  # Mã trang web cho username/email
    metadata_key = Concat(METADATA_KEY_PREFIX, website_key)

    on_store_credentials = Seq([
        Assert(Txn.sender() == App.globalGet(OWNER_KEY)),
        App.localPut(Int(0), username_key, Txn.application_args[2]),  # Lưu username/email
        App.localPut(Int(0), password_key, Txn.application_args[3]),  # Lưu mật khẩu mã hóa
        App.localPut(Int(0), metadata_key, Txn.application_args[4]),  # Lưu metadata (website, ghi chú)
        Approve()
    ])

    # Chức năng truy xuất email/username và mật khẩu, không trả về trực tiếp
    on_retrieve_credentials = Seq([
        Assert(Txn.sender() == App.globalGet(OWNER_KEY)),
        Log(Concat(
            App.localGet(Int(0), username_key), Bytes(":"), App.localGet(Int(0), password_key)
        )),  # Ghi lại log với username và mật khẩu
        Approve()
    ])

    # Chức năng cập nhật email/username và mật khẩu
    on_update_credentials = Seq([
        Assert(Txn.sender() == App.globalGet(OWNER_KEY)),
        App.localPut(Int(0), username_key, Txn.application_args[2]),  # Cập nhật username/email
        App.localPut(Int(0), password_key, Txn.application_args[3]),  # Cập nhật mật khẩu mã hóa
        App.localPut(Int(0), metadata_key, Txn.application_args[4]),  # Cập nhật metadata
        Approve()
    ])

    # Chức năng xóa email/username và mật khẩu
    on_delete_credentials = Seq([
        Assert(Txn.sender() == App.globalGet(OWNER_KEY)),
        App.localDel(Int(0), username_key),  # Xóa username/email
        App.localDel(Int(0), password_key),  # Xóa mật khẩu
        App.localDel(Int(0), metadata_key),  # Xóa metadata
        Approve()
    ])

    # Router điều hướng các chức năng
    program_router = Cond(
        [Txn.application_id() == Int(0), on_register],  # Đăng ký
        [Txn.application_args[0] == Bytes("store_credentials"), on_store_credentials],  # Lưu thông tin đăng nhập
        [Txn.application_args[0] == Bytes("retrieve_credentials"), on_retrieve_credentials],  # Truy xuất thông tin
        [Txn.application_args[0] == Bytes("update_credentials"), on_update_credentials],  # Cập nhật thông tin
        [Txn.application_args[0] == Bytes("delete_credentials"), on_delete_credentials]  # Xóa thông tin
    )

    return program_router

def clear_state_program():
    return Approve()

# Tạo chương trình PyTeal và xuất ra file TEAL
if __name__ == "__main__":
    approval = approval_program()
    clear = clear_state_program()

    compiled_approval = compileTeal(approval, mode=Mode.Application, version=5)
    compiled_clear = compileTeal(clear, mode=Mode.Application, version=5)

    # Xuất ra file TEAL
    with open("approval.teal", "w") as approval_file:
        approval_file.write(compiled_approval)

    with open("clear.teal", "w") as clear_file:
        clear_file.write(compiled_clear)

    print("Approval Program TEAL đã được xuất ra file approval.teal")
    print("Clear State Program TEAL đã được xuất ra file clear.teal")