import requests
import time
import threading
def get():
    r = requests.get('http://my-deploy-lb-1005870485.us-east-1.elb.amazonaws.com/tasks/')
    # print(r.json())
    return r

def post(title, date, description):
    r = requests.post('http://my-deploy-lb-1005870485.us-east-1.elb.amazonaws.com/tasks/', data={'title': title, 'pub_date': date, 'description': description})
    # print(r.json())
    return r

# get()

if __name__ == "__main__":
    users = 0
    while True:
        if users<1000:
            users+=50
            print(users)
        for i in range(users):
            x = threading.Thread(target=get)
            x.start()
        time.sleep(1)

