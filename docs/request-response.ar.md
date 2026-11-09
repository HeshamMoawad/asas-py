# أجسام الطلب والاستجابات

يتكامل أساس مع [Pydantic](https://docs.pydantic.dev/) على طرفَي النداء: نماذج Pydantic تدخل
بوصفها جسم الطلب، و**تعليق نوع القيمة المُعادة** يتحقّق ممّا **يخرج**.

## إرسال جسم طلب

أي وسيط يكون تعليقه نموذج Pydantic (`BaseModel`) — أو قائمة منها، أو `dict` — يُسلسَل إلى JSON
ويُرسَل بوصفه جسم الطلب:

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
    @post("/users")
    def create_user(self, payload: CreateUser) -> User:
        raise NotImplementedError


client = MyClient(base_url="https://api.example.com")
client.create_user(CreateUser(name="Ada", email="ada@example.com"))
# body: {"name": "Ada", "email": "ada@example.com"}
```

تتحوّل قائمة النماذج إلى مصفوفة JSON، ويُرسَل `dict` ككائن JSON:

```python
class BulkClient(AsasClient):
    @post("/users/bulk")
    def create_users(self, payload: list[CreateUser]) -> list[User]:
        raise NotImplementedError

    @post("/events")
    def send_event(self, payload: dict[str, str]) -> None:
        raise NotImplementedError
```

يُفرَّغ الجسم بوضع JSON وبحسب الاسم المستعار، فتُسلسَل `datetime` و`UUID` و`Decimal`
والتعدادات والحقول ذات الأسماء المستعارة بصورة صحيحة. وللتحكّم في التفريغ (مثلًا للتحديثات
الجزئية) استخدم علامة [`Body`](parameters.md):

```python
from typing import Annotated

from pydantic import BaseModel

from asas import AsasClient, Body, patch


class UserPatch(BaseModel):
    name: str | None = None
    email: str | None = None


class PatchClient(AsasClient):
    @patch("/users/{id}")
    def update_user(
        self, id: int, changes: Annotated[UserPatch, Body(exclude_unset=True)]
    ) -> None:
        raise NotImplementedError
```

وللنماذج والملفات والترويسات والكوكيز راجع [الوسائط](parameters.md).

## تحليل الاستجابة

يحدّد تعليق نوع القيمة المُعادة ما تحصل عليه:

| تعليق نوع القيمة المُعادة | النتيجة |
| --- | --- |
| `Response` | كائن [`Response`](models.md#response) الخام |
| `None` | `None`؛ ويُهمَل الجسم |
| `bytes` | `response.content` |
| `str` | `response.text` |
| `bytes \| None`، `str \| None` | كما سبق، أو `None` إذا كان الجسم فارغًا |
| أي نوع آخر `T` | `TypeAdapter(T).validate_json(response.content)` |

ولأن مسار النماذج يستخدم `TypeAdapter` من Pydantic، فأي تركيب من الأنواع يعمل: نموذج مفرد،
و`list[Model]`، و`dict[str, Model]`، والاتحادات، وهكذا.

=== "نموذج مفرد"

    ```python
    from pydantic import BaseModel

    from asas import AsasClient, get


    class User(BaseModel):
        id: int
        name: str


    class MyClient(AsasClient):
        @get("/users/{id}")
        def get_user(self, id: int) -> User:
            raise NotImplementedError


    client = MyClient(base_url="https://api.example.com")
    user = client.get_user(1)   # -> User(id=1, name="...")
    ```

=== "قائمة نماذج"

    ```python
    from pydantic import BaseModel

    from asas import AsasClient, get


    class User(BaseModel):
        id: int
        name: str


    class MyClient(AsasClient):
        @get("/users")
        def get_users(self) -> list[User]:
            raise NotImplementedError
    ```

=== "استجابة خام"

    ```python
    from asas import AsasClient, Response, get


    class MyClient(AsasClient):
        @get("/health")
        def health(self) -> Response:
            raise NotImplementedError


    client = MyClient(base_url="https://api.example.com")
    response = client.health()
    print(response.status_code, response.json())
    ```

نقطة النهاية المُعلَّقة بـ `-> Response` لا ترفع خطأً بسبب الحالة أبدًا، فيمكنك فحص أي رمز حالة
بنفسك. أما كل نوع إعادة آخر فيرفع [خطأً مكتوب النوع](errors.md) عند استجابة غير 2xx.

### الأجسام الفارغة

إذا كان الجسم فارغًا، فإن نقطة النهاية التي يقبل نوع قيمتها المُعادة `None` تعيد `None`:

```python
from pydantic import BaseModel

from asas import AsasClient, get


class Profile(BaseModel):
    bio: str


class MyClient(AsasClient):
    @get("/users/{id}/profile")
    def profile(self, id: int) -> Profile | None:
        raise NotImplementedError   # e.g. a 204 with no body returns None
```

أما لأي نوع نموذج آخر فالجسم الفارغ يرفع [`ResponseValidationError`](errors.md). وكذلك الجسم
الذي ليس JSON صالحًا أو لا يطابق النموذج.

## الجمع بين نموذجَي الجسم والاستجابة

تستخدم نقطة نهاية نموذجية للإنشاء والإعادة كليهما معًا، دون أي كود إضافي:

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
    @post("/users")
    def create_user(self, payload: CreateUser) -> User:
        raise NotImplementedError


client = MyClient(base_url="https://api.example.com")
created = client.create_user(CreateUser(name="Ada", email="ada@example.com"))
# `payload` is sent as the JSON body; the response is validated into `User`.
```

!!! tip "المعالجة اللاحقة"
    لا يُنفَّذ جسم الدالة أبدًا، فلإعادة تشكيل نتيجة اكتب دالة عادية تستدعي نقطة النهاية، أو
    استخدم [خطّافًا](hooks.md).
