import gevent.monkey
gevent.monkey.patch_all()
import requests
import time

def make_get(LB_DNS):
    r = requests.get(f'http://{LB_DNS}/tasks/')
    print(r.json())
    return r

def make_post(LB_DNS, title, date, description):
    r = requests.post(f'http://{LB_DNS}/tasks/', data={'title': title, 'pub_date': date, 'description': description})
    print(r.json())
    return r

# get()

if __name__ == "__main__":
    lb_dns = "my-deploy-LB-806019030.us-east-1.elb.amazonaws.com"
    while True:
        digit = input('Digite 1 para get e 2 para post ou 0 para finalizar: ')
        if digit == "1":
            make_get(lb_dns)
        if digit == "2":
            title       = input("Digite o titulo da tarefa: ")
            year        = input("Digite o ano para conclusao: ")
            month       = input("Digite o mes para conclusao: ")
            day         = input("Digite o dia para conclusao: ")
            hour        = input("Digite o horario para conclusao: ")
            minute      = input("Digite o minuto para conclusao: ")
            description = input("Digite a descricao da tarefa: ")
            date        = f"{year}-{month}-{day}T{hour}:{minute}"
            print(f"A tarefa '{title}' tem data de conclusao para {date} com a descricao '{description}'")
            confirm     = input("Digite 1 para confirmar ou 0 para cancelar: ")
            if confirm:
                make_post(lb_dns, title, date, description)
        if digit == "0":
            quit()
