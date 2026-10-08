import requests

BASE = "https://pycourse-2026.duckdns.org/coffee/hot"
MARKER = "lab-linaalewii"   

RUN_A = False    
RUN_B = False 
RUN_C = True   

created_ids = []   


def show(r):
    print(r.request.method, r.url)
    print("  status:      ", r.status_code)
    print("  content-type:", r.headers.get("Content-Type"))
    print("  body:        ", r.text[:300])
    print("-" * 50)


def remember(r):
    """Запомнить id созданной записи, чтобы потом её удалить."""
    if r.ok and "json" in r.headers.get("Content-Type", "").lower():
        try:
            body = r.json()
        except ValueError:
            return
        if isinstance(body, dict) and "id" in body:
            created_ids.append(body["id"])


def cleanup():
    """Удаляет только записи с нашей меткой в title."""
    print("\n=== ОЧИСТКА ===")
    for drink_id in created_ids:
        r = requests.get(f"{BASE}/{drink_id}", timeout=10)
        if not r.ok:
            print("id", drink_id, "уже нет или недоступен")
            continue
        try:
            data = r.json()
        except ValueError:
            continue
        marked = MARKER in str(data.get("title")) or MARKER in str(data.get("description"))
        if marked:
            d = requests.delete(f"{BASE}/{drink_id}", timeout=10)
            print("удалён id", drink_id, "статус", d.status_code)
        else:
            print("ПРОПУЩЕН id", drink_id, "- нет нашей метки, не трогаем")


def part_a():
    print("=== A1. GET коллекции ===")
    r = requests.get(BASE + "/", timeout=10)
    show(r)
    data = r.json()
    print("тип:", type(data).__name__, "| записей:", len(data))
    print("первая запись:", data[0])
    print("типы полей:", {k: type(v).__name__ for k, v in data[0].items()})

    print("=== A2. GET одного ресурса ===")
    show(requests.get(BASE + "/2", timeout=10))

    print("=== A3. GET несуществующего ===")
    show(requests.get(BASE + "/999999", timeout=10))

    print("=== A4. OPTIONS ===")
    r = requests.options(BASE + "/", timeout=10)
    show(r)
    print("Allow:", r.headers.get("Allow"))


def make_body(**overrides):
    body = {
        "title": f"Test latte {MARKER}",
        "description": "тестовый напиток",
        "ingredients": ["Espresso", "Steamed milk"],
        "image": "",
        "description": f"тестовый напиток {MARKER}",
    }
    body.update(overrides)
    return body


def part_b():
    print("=== B1. Нормальный POST ===")
    r = requests.post(BASE, json=make_body(), timeout=10)
    show(r)
    remember(r)

   
    experiments = []
    for field in ("description", "ingredients", "image"):
        body = make_body()
        del body[field]
        experiments.append((f"без поля {field}", body))
    body = make_body()
    del body["title"]
    body["description"] = f"без title {MARKER}"  
    experiments.append(("без поля title", body))
    experiments += [
        ("ingredients - строка", make_body(ingredients="milk")),
        ("пустой title", make_body(title="")),
        ("лишнее поле foo", make_body(foo=1)),
    ]
    for name, body in experiments:
        print(f"=== B. {name} ===")
        r = requests.post(BASE, json=body, timeout=10)
        show(r)
        remember(r)

RUN_B2 = False

def part_b2():
    experiments = [
        ("title - число", make_body(title=123)),
        ("ingredients - список чисел", make_body(ingredients=[1, 2])),
        ("image - число", make_body(image=5)),
    ]
    for name, body in experiments:
        print(f"=== B2. {name} ===")
        r = requests.post(BASE, json=body, timeout=10)
        show(r)
        remember(r)

def part_c():
    print("=== C0. Создаём запись для экспериментов ===")
    r = requests.post(BASE, json=make_body(), timeout=10)
    show(r)
    remember(r)
    my_id = r.json()["id"]
    url = f"{BASE}/{my_id}"

    print("=== C1. PUT полным телом ===")
    full = make_body(title=f"Test mocha {MARKER}", description="заменено",
                     ingredients=["Espresso", "Chocolate"])
    show(requests.put(url, json=full, timeout=10))
    show(requests.get(url, timeout=10))

    print("=== C2. PUT только с title (проверяем, пропадут ли остальные поля) ===")
    show(requests.put(url, json={"title": f"Only title {MARKER}"}, timeout=10))
    show(requests.get(url, timeout=10))

    print("=== C3. PATCH одного поля ===")
    show(requests.patch(url, json={"description": "изменено PATCH"}, timeout=10))
    show(requests.get(url, timeout=10))

    print("=== C4. DELETE ===")
    r = requests.delete(url, timeout=10)
    show(r)
    print("  длина тела DELETE:", len(r.content))

    print("=== C5. GET после DELETE ===")
    show(requests.get(url, timeout=10))


if __name__ == "__main__":
    try:
        if RUN_A:
            part_a()
        if RUN_B:
            part_b()
        if RUN_B2:
            part_b2()
        if RUN_C:
            part_c()
    finally:
        cleanup()