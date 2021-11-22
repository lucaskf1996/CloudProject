import requests

def get():
    r = requests.get('http://teste-1923920199.us-east-1.elb.amazonaws.com/tasks/')
    print(r.json())
    return r

def post(title, date, description):
    r = requests.post('http://teste-1923920199.us-east-1.elb.amazonaws.com/tasks/', data={'title': title, 'pub_date': date, 'description': description})
    print(r.json())
    return r

# get()

if __name__ == "__main__":
    while True:
        digit = input('Digite 1 para get e 2 para post ou 0 para finalizar: ')
        if digit == "1":
            get()
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
                post(title, date, description)
        if digit == "0":
            quit()
