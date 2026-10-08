"""Клиент SampleAPIs Coffee (горячие напитки).

ОПИСАНИЕ ЗАПРОСА СОЗДАНИЯ ГОРЯЧЕГО КОФЕ
=======================================
Метод и URL:
    POST https://pycourse-2026.duckdns.org/coffee/hot/

Заголовки:
    Content-Type: application/json  (requests ставит сам при json=...)
    Accept: application/json

Тело запроса (JSON-объект):
    title        string         название напитка
    description  string         описание напитка
    ingredients  array[string]  состав напитка
    image        string         ссылка на картинку (допустима пустая строка "")
    id           integer        НЕ отправляется: его назначает сервер

Обязательные поля: title, description, ingredients, image.
    Подтверждено запросами: без любого из этих четырёх полей сервер
    возвращает 400 (в теле: error, message, expected, received).

Что сервер НЕ проверяет (подтверждено запросами, ответ 201):
    - ingredients строкой вместо массива ("milk");
    - пустой title ("");
    - лишние поля (например, foo=1 сохраняется в записи).

Ограничения, которые проверяет только наш клиент (validate_drink):
    - title и description - непустые строки;
    - image - строка;
    - ingredients - непустой список непустых строк;
    - неизвестные поля запрещены.

Кто задаёт поля:
    клиент - title, description, ingredients, image;
    сервер - id (целое число, после удаления номер может быть выдан снова).

Успешный ответ: статус 201, Content-Type application/json, тело - созданный
    объект целиком вместе с назначенным id.

Другие факты об API (подтверждены запросами):
    - GET несуществующего id: 404 с телом {} (JSON), поэтому статус надо
      проверять до использования тела;
    - PUT требует все поля (иначе 400, запись не меняется), id в теле не нужен;
    - PATCH меняет только переданные поля;
    - DELETE: 200 и тело {}; после удаления GET даёт 404.
"""

import requests
from uuid import uuid4

JsonObject = dict[str, object]

DRINK_FIELDS = ("title", "description", "ingredients", "image")


class CoffeeApiError(Exception):
    pass


class CoffeeNotFoundError(CoffeeApiError):
    pass


class CoffeeTimeoutError(CoffeeApiError):
    pass


def validate_drink(payload: JsonObject, partial: bool = False) -> None:
    """Локальная проверка значений (серверу эти правила не нужны).

    partial=True - для PATCH: проверяем только переданные поля.
    """
    unknown = set(payload) - set(DRINK_FIELDS)
    if unknown:
        raise ValueError(f"неизвестные поля: {sorted(unknown)}")

    if not partial:
        missing = [name for name in DRINK_FIELDS if name not in payload]
        if missing:
            raise ValueError(f"не хватает полей: {missing}")

    for name in ("title", "description"):
        if name in payload:
            value = payload[name]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} должно быть непустой строкой")

    if "image" in payload and not isinstance(payload["image"], str):
        raise ValueError("image должно быть строкой")

    if "ingredients" in payload:
        ingredients = payload["ingredients"]
        if (
            not isinstance(ingredients, list)
            or not ingredients
            or not all(isinstance(i, str) and i.strip() for i in ingredients)
        ):
            raise ValueError("ingredients - непустой список непустых строк")


class SampleApisCoffeeClient:
    def __init__(
        self,
        base_url: str = "https://pycourse-2026.duckdns.org/coffee/hot",
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def list_drinks(self) -> list[JsonObject]:
        response = self._request("GET")
        data = self._read_json(response)
        if not isinstance(data, list):
            raise CoffeeApiError("ожидался JSON-массив")
        return data

    def get_drink(self, drink_id: int) -> JsonObject:
        response = self._request("GET", f"/{drink_id}")
        return self._read_object(response)

    def create_drink(self, payload: JsonObject) -> JsonObject:
        validate_drink(payload)
        response = self._request("POST", "", payload)
        return self._read_object(response)

    def replace_drink(
        self,
        drink_id: int,
        payload: JsonObject,
    ) -> JsonObject:
        validate_drink(payload)
        response = self._request("PUT", f"/{drink_id}", payload)
        return self._read_object(response)

    def update_drink(
        self,
        drink_id: int,
        changes: JsonObject,
    ) -> JsonObject:
        validate_drink(changes, partial=True)
        response = self._request("PATCH", f"/{drink_id}", changes)
        return self._read_object(response)

    def delete_drink(self, drink_id: int) -> None:
        # Тело ответа не разбираем: клиенту оно не нужно.
        self._request("DELETE", f"/{drink_id}")

    def _request(
        self,
        method: str,
        path: str = "",
        payload: JsonObject | None = None,
    ) -> requests.Response:
        url = self._base_url + path
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            )
        except requests.Timeout as error:
            raise CoffeeTimeoutError(
                f"{method} {url}: тайм-аут, результат неизвестен"
            ) from error
        except requests.RequestException as error:
            raise CoffeeApiError(f"{method} {url}: сетевая ошибка: {error}") from error

        print(f"    {method} {url} -> {response.status_code}")

        # 404 проверяем раньше общей ошибки, чтобы отличать его от остальных.
        if response.status_code == 404:
            raise CoffeeNotFoundError(f"{method} {url}: 404, ресурс не найден")
        if not response.ok:
            raise CoffeeApiError(
                f"{method} {url}: статус {response.status_code}, "
                f"тело: {response.text[:200]}"
            )
        return response

    @staticmethod
    def _read_json(response: requests.Response) -> object:
        # Статус уже проверен в _request, теперь проверяем формат ответа.
        content_type = response.headers.get("Content-Type", "")
        if "json" not in content_type.lower():
            raise CoffeeApiError(f"ожидался JSON, пришло: {content_type!r}")
        try:
            return response.json()
        except ValueError as error:
            raise CoffeeApiError("тело ответа - невалидный JSON") from error

    def _read_object(self, response: requests.Response) -> JsonObject:
        data = self._read_json(response)
        if not isinstance(data, dict):
            raise CoffeeApiError("ожидался JSON-объект")
        return data


def check_fields(actual: JsonObject, expected: JsonObject, step: str) -> None:
    """Проверяет, что поля из expected совпадают с полями ответа."""
    for key, value in expected.items():
        if actual.get(key) != value:
            raise CoffeeApiError(
                f"{step}: поле {key!r}: ожидали {value!r}, "
                f"получили {actual.get(key)!r}"
            )


def main() -> int:
    client = SampleApisCoffeeClient()
    marker = uuid4().hex[:8]
    created_id = 999999
    try:
        print("1. GET список горячих напитков")
        drinks = client.list_drinks()
        print(f"   получено записей: {len(drinks)}")

        print(f"2. POST создание (метка группы: {marker})")
        payload: JsonObject = {
            "title": f"Test latte {marker}",
            "description": f"Тестовый напиток группы {marker}",
            "ingredients": ["Espresso", "Steamed milk"],
            "image": "",
        }
        try:
            created = client.create_drink(payload)
        except CoffeeTimeoutError:
            print(
                "   POST завершился тайм-аутом: запись могла создаться. "
                f"Проверьте вручную по метке {marker}. Повтор не делаем."
            )
            return 1
        new_id = created.get("id")
        if not isinstance(new_id, int):
            raise CoffeeApiError(f"в ответе POST нет числового id: {created}")
        created_id = new_id  # сразу запоминаем, чтобы finally мог удалить
        print(f"   создана запись id={created_id}")

        print("3. GET созданной записи по id")
        fetched = client.get_drink(created_id)
        check_fields(fetched, payload, "GET после POST")
        print("   данные совпадают с отправленными")

        print("4. PUT полная замена")
        replacement: JsonObject = {
            "title": f"Test mocha {marker}",
            "description": f"Заменённое описание {marker}",
            "ingredients": ["Espresso", "Chocolate"],
            "image": "",
        }
        client.replace_drink(created_id, replacement)
        fetched = client.get_drink(created_id)
        check_fields(fetched, replacement, "GET после PUT")
        print("   все поля заменены")

        print("5. PATCH частичное изменение")
        changes: JsonObject = {"description": f"Изменено через PATCH {marker}"}
        client.update_drink(created_id, changes)

        print("6. GET: проверка PATCH и сохранности остальных полей")
        fetched = client.get_drink(created_id)
        check_fields(fetched, {**replacement, **changes}, "GET после PATCH")
        print("   изменилось только описание, остальное сохранилось")

        print("7. DELETE")
        client.delete_drink(created_id)

        print("8. GET удалённой записи, ожидаем 404")
        try:
            client.get_drink(created_id)
        except CoffeeNotFoundError:
            print("   получен ожидаемый 404, запись удалена")
            created_id = None
        else:
            raise CoffeeApiError("запись всё ещё доступна после DELETE")
    except (CoffeeApiError, ValueError) as error:
        print(f"Ошибка: {error}. Метка группы: {marker}")
        return 1
    finally:
        if created_id is not None:
            try:
                client.delete_drink(created_id)
                print(f"Очистка: удалена запись id={created_id}")
            except CoffeeNotFoundError:
                pass
            except CoffeeApiError as error:
                print(f"Не удалось удалить id={created_id}: {error}")
    print("Сценарий выполнен успешно")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())