# التوجيه

يوفّر أساس مزخرفًا واحدًا لكل دالة HTTP. يحوّل كل منها دالةً في عميلك إلى نقطة نهاية مكتوبة
الأنواع.

| المزخرف | دالة HTTP |
| --- | --- |
| `@get` | `GET` |
| `@post` | `POST` |
| `@put` | `PUT` |
| `@delete` | `DELETE` |
| `@patch` | `PATCH` |

تأخذ المزخرفات الخمسة الوسائط نفسها:

```python
def get(
    path, *, headers=None, timeout=None, use_auth=True, raise_for_status=None, hooks=None
): ...
```

- **`path`** — مسار نقطة النهاية، يُلحق بـ `base_url` الخاص بالعميل. قد يحتوي على مقاطع
  `{placeholder}`.
- **`headers`** — قاموس ترويسات تُرسَل مع نقطة النهاية هذه فقط. راجع
  [أسبقية الترويسات](parameters.md).
- **`timeout`** — مهلة لكل طلب بالثواني. يطبّقها محرّكا `httpx` و`requests` المرفقان.
- **`use_auth`** — اضبطه على `False` لتخطّي مصادقة العميل لهذه النقطة (انظر أدناه).
- **`raise_for_status`** — `True` أو `False` لتجاوز إعداد العميل لهذه النقطة؛ والقيمة `None`
  (الافتراضية) ترث إعداد العميل. راجع [متى تُرفع الأخطاء](errors.md).
- **`hooks`** — كائن [`Hooks`](hooks.md) يعمل بعد خطافات العميل.

`path` هو الوسيط الموضعي الوحيد؛ وكل ما عداه مفتاحي فقط. لم يعد الوسيط `response_model` من
الإصدار 0.1 موجودًا — فقد حلّ محلّه تعليق نوع القيمة المُعادة.

## تعريف نقطة نهاية

**تعليق نوع القيمة المُعادة** يخبر أساس كيف يحلّل الاستجابة، و**الوسائط** تخبره كيف يبني
الطلب. جسم الدالة لا يُنفَّذ أبدًا، لذا فالاصطلاح أن تكتب `raise NotImplementedError` (أما
`...` المجرّدة فيرفضها `mypy --strict` بالخطأ `[empty-body]`):

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
user = client.get_user(1)       # GET /users/1  ->  User
```

المزخرفات مكتوبة الأنواع بحيث يرى المستدعون التوقيع الذي كتبته كما هو:
`client.get_user(1)` هو `User` بالنسبة إلى mypy ومحرّر الكود. لا يُحقَن أي وسيط، ولا يُمرَّر
شيء إلى جسم الدالة.

إن أردت معالجة النتيجة لاحقًا، فاكتب دالة عادية تستدعي نقطة النهاية، أو استخدم
[خطّافًا](hooks.md):

```python
class MyClient(AsasClient):
    @get("/users/{id}")
    def get_user(self, id: int) -> User:
        raise NotImplementedError

    def get_username(self, id: int) -> str:
        return self.get_user(id).name
```

## تعليقات نوع القيمة المُعادة

| تعليق نوع القيمة المُعادة | النتيجة |
| --- | --- |
| `Response` | كائن [`Response`](models.md#response) الخام؛ ولا يرفع خطأً بسبب الحالة أبدًا |
| `None` | `None`؛ ويُهمَل الجسم |
| `bytes` | `response.content` |
| `str` | `response.text` |
| `bytes \| None`، `str \| None` | كما سبق، أو `None` إذا كان الجسم فارغًا |
| أي نوع آخر `T` | الجسم متحقَّقًا منه بوصفه `T` عبر `TypeAdapter` من Pydantic |

راجع [أجسام الطلب والاستجابات](request-response.md) للتفاصيل، بما فيها الأجسام الفارغة.
غياب تعليق نوع القيمة المُعادة يرفع `TypeError` — استخدم `-> Response` عندما تريد الاستجابة
الخام.

## كيف تُوجَّه الوسائط

يُوجَّه كل وسيط بعلامة (marker)، أو يُستنتج من تعليق نوعه عندما لا تعطيه علامة:

| الوسيط | يُوجَّه إلى |
| --- | --- |
| اسمه يطابق `{placeholder}` في المسار | يُستبدل داخل عنوان URL |
| تعليقه `BaseModel` أو `list[BaseModel]` أو `dict` | جسم الطلب بصيغة JSON |
| أي شيء آخر | وسيط استعلام |

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
    @post("/teams/{id}/users")
    def create_user(self, id: int, payload: CreateUser, team: str) -> User:
        raise NotImplementedError


client = MyClient(base_url="https://api.example.com")
client.create_user(
    42,                                                  # -> URL path
    CreateUser(name="Ada", email="ada@x.com"),           # -> JSON body
    team="core",                                         # -> query string
)
# POST https://api.example.com/teams/42/users?team=core
# body: {"name": "Ada", "email": "ada@x.com"}
```

يُحسم التوجيه من **تعليقات الأنواع وقت الزخرفة**، لا من القيم التي تمرّرها وقت الاستدعاء.
وللترويسات والكوكيز والنماذج والملفات والأسماء المستعارة، استخدم العلامات الموضّحة في
[الوسائط](parameters.md).

أي وسيط قيمته `None` يُسقَط من الاستعلام والترويسات والكوكيز والنموذج، ما يجعل الوسائط
الاختيارية سهلة:

```python
class SearchClient(AsasClient):
    @get("/search")
    def search(self, q: str, page: int | None = None) -> dict:
        raise NotImplementedError


client = SearchClient(base_url="https://api.example.com")
client.search("asas")            # GET /search?q=asas
client.search("asas", page=2)    # GET /search?q=asas&page=2
```

!!! note "أخطاء التعريف تفشل مبكرًا"
    أخطاء مثل `{placeholder}` بلا وسيط مطابق، أو تعليق نوع مفقود، أو `*args` / `**kwargs` على
    نقطة نهاية، ترفع `TypeError` عند تعريف الفئة. راجع
    [الوسائط](parameters.md).

!!! warning "المراجع الأمامية تُفحص عند أول استدعاء"
    إن لم يكن نوع القيمة المُعادة أو نوع وسيط معرَّفًا بعد وقت زخرفة نقطة النهاية (مثلًا نموذج
    معرَّف أسفل الوحدة مع تعليقات نصية)، يؤجّل أساس التصريف إلى **أول استدعاء**. وعندها تظهر
    أخطاء `TypeError` الخاصة بالتعريف لنقطة النهاية تلك عند أول استدعاء بدلًا من وقت
    الاستيراد. عرِّف النماذج على مستوى الوحدة: فالنماذج المنشأة داخل جسم دالة لا يمكن حلّها من
    التعليقات النصية.

## متزامن وغير متزامن، بمزخرف واحد

تعمل المزخرفات نفسها مع دوال `def` و`async def` معًا — يكتشف أساس دوال الكوروتين تلقائيًا
ويستخدم المسار غير المتزامن للمحرّك. وتُعيد `async def ... -> User` قيمة `User` عند انتظارها.

```python
from pydantic import BaseModel

from asas import AsasAsyncClient, get


class User(BaseModel):
    id: int
    name: str


class AsyncClient(AsasAsyncClient):
    @get("/users/{id}")
    async def get_user(self, id: int) -> User:
        raise NotImplementedError
```

!!! note
    استدعاء نقطة نهاية `async def` على محرّك متزامن (أو العكس) يرفع `TypeError` واضحًا يخبرك
    بأي بروتوكول يفتقر إليه المحرّك.

## التحكم في المصادقة لكل نقطة نهاية

حتى عندما يملك العميل استراتيجية مصادقة عامة، يمكنك تعطيلها لنقاط نهاية عامة محدّدة عبر
`use_auth=False`:

```python
from asas import AsasClient, get


class MyClient(AsasClient):
    @get("/public-data", use_auth=False)
    def get_public(self) -> dict:
        raise NotImplementedError
```

هذا أيضًا ما تستخدمه لنقطة نهاية تسجيل الدخول التي *تنتج* رمزك — راجع مثال المصادقة أثناء
التشغيل في [العملاء](clients.md).
