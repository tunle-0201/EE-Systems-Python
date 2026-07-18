import time
flight_log = []
while True:
    user_command = input("Nhap lenh: ")
    if user_command == "exit":
        break
    elif user_command.startswith("log:"):
        altitude = int(user_command.split(":")[1])
        log_entry = {'time':time.time(),'altitude':altitude}
        flight_log.append(log_entry)
        print(f"Da ghi nhan do cao {altitude}m vao luc {time.ctime(log_entry['time'])}")
    elif user_command == "show":
        for entry in flight_log:
            print(f"Do cao {entry['altitude']}m luc {time.ctime(entry['time'])}")
    elif user_command =="alert":
        danger = False
        for entry in flight_log:
            if entry['altitude'] >=10000:
                danger = True
                break
        if danger:
            print("Warning: Do cao vuot nguong an toan!")
        else:
            print("Do cao trong gioi han")

