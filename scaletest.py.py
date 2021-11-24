import requests
import time
import threading
def get(LB_DNS):
    r = requests.get(f'http://{LB_DNS}/tasks/')
    # print(r.json())
    return r

def post(LB_DNS, title, date, description):
    r = requests.post(f'http://{LB_DNS}/tasks/', data={'title': title, 'pub_date': date, 'description': description})
    # print(r.json())
    return r

# get()

if __name__ == "__main__":
    users = 0
    lb_dns = "insert dns here"
    while True:
        if users<1000:
            users+=50
            print(users)
        for i in range(users):
            x = threading.Thread(target=get, args=[lb_dns])
            x.start()
        time.sleep(1)

