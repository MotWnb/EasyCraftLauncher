def main_settings():

    def java_settings():

        def java_settings_choose():
            pass

        def java_settings_java_downloads():
            pass

        def java_settings_search():
            pass

        def java_settings_user_import():
            pass

        choice = input("请输入你想要进入的选项(请输入对应的序号)\n"
                       "1.游戏Java版本选择\n"
                       "2.游戏Java版本下载\n"
                       "3.自动搜索Java\n"
                       "4.手动导入Java\n"
                       "请选择:")

        if choice == "1":
            java_settings_choose()
        elif choice == "2":
            java_settings_java_downloads()
        elif choice == "3":
            java_settings_search()
        elif choice == "4":
            java_settings_user_import()

    def game_settings():
        pass

    def download_settings():
        pass


    choice = input("请输入你想要进入的选项(请输入对应的序号)\n"
                       "1.Java设置\n"
                       "2.游戏设置\n"
                       "3.下载设置\n"
                       "请选择:")
    if choice == "1":
        java_settings()
    elif choice == "2":
        game_settings()
    elif choice == "3":
        download_settings()
