# أجسام الطلب والاستجابات

يتكامل أساس مع [Pydantic](https://docs.pydantic.dev/) على طرفَي النداء: نماذج Pydantic تدخل
بوصفها جسم الطلب، و`response_model` يتحقّق ممّا يخرج.

## إرسال جسم طلب

أي وسيط يكون نموذج Pydantic (`BaseModel`) — أو قائمة منها — يُسلسَل إلى JSON ويُرسَل بوصفه
جسم الطلب:

```python
from pydantic import BaseModel
from asas import AsasClient, post, Response

class CreateUser(BaseModel):
    name: str
    email: str

class MyClient(AsasClient):
    @post("/users")
    def create_user(self, response: Response, payload: CreateUser):
        return response.json()

client = MyClient(base_url="https://api.example.com")
client.create_user(payload=CreateUser(name="Ada", email="ada@example.com"))
# body: {"name": "Ada", "email": "ada@example.com"}
```

تتحوّل قائمة النماذج إلى مصفوفة JSON:

```python
@post("/users/bulk")
def create_users(self, response: Response, payload: list[CreateUser]):
    return response.json()
```

!!! warning "القاموس ليس جسمًا"
    تُوجَّه نماذج Pydantic فقط إلى الجسم. أما وسيط القاموس (`dict`) العادي فيُعامَل بوصفه
    وسائط استعلام. غلِّف بيانات الجسم دائمًا في `BaseModel`.

## التحقق من الاستجابة

مرِّر `response_model` إلى مزخرف ليتحقّق أساس من JSON الاستجابة عبر
[`TypeAdapter`](https://docs.pydantic.dev/latest/concepts/type_adapter/) من Pydantic قبل
تسليمها إلى دالتك. يدعم هذا النماذج البسيطة و`List[Model]` وتركيبات أنواع أخرى:

=== "نموذج مفرد"

    ```python
    from pydantic import BaseModel
    from asas import AsasClient, get

    class User(BaseModel):
        id: int
        name: str

    class MyClient(AsasClient):
        @get("/users/{id}", response_model=User)
        def get_user(self, user: User, id: int) -> User:
            return user

    client = MyClient(base_url="https://api.example.com")
    user = client.get_user(id=1)   # -> User(id=1, name="...")
    ```

=== "قائمة نماذج"

    ```python
    from typing import List
    from pydantic import BaseModel
    from asas import AsasClient, get

    class User(BaseModel):
        id: int
        name: str

    class MyClient(AsasClient):
        @get("/users", response_model=List[User])
        def get_users(self, users: List[User]) -> List[User]:
            return users
    ```

عند **حذف** `response_model`، يُحقَن كائن [`Response`](models.md#response) الخام بدلًا من ذلك،
وتستدعي `response.json()` بنفسك.

## الجمع بين نموذجَي الجسم والاستجابة

تستخدم نقطة نهاية نموذجية للإنشاء والإعادة كليهما معًا:

```python
from pydantic import BaseModel
from asas import AsasClient, post

class CreateUser(BaseModel):
    name: str
    email: str

class User(BaseModel):
    id: int
    name: str
    email: str

class MyClient(AsasClient):
    @post("/users", response_model=User)
    def create_user(self, user: User, payload: CreateUser) -> User:
        return user

client = MyClient(base_url="https://api.example.com")
created = client.create_user(payload=CreateUser(name="Ada", email="ada@example.com"))
# يُرسَل `payload` بوصفه جسم JSON؛ ويُتحقَّق من الاستجابة وتُحوَّل إلى `User`.
```

!!! tip "الأجسام الفارغة لا بأس بها"
    لأن أساس يعيد النتيجة المُحلَّلة عندما يعيد جسم دالتك `None`، يمكن ترك جسم الدالة سطرًا
    واحدًا `return user` (أو حتى `...`) لأجل تحديد الأنواع فقط. راجع
    [اصطلاح القيمة المُعادة](routing.md).
