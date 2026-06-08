# التوجيه والوسائط

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
@get(path, response_model=None, use_auth=True)
```

- **`path`** — مسار نقطة النهاية، يُلحق بـ `base_url` الخاص بالعميل. قد يحتوي على مقاطع
  `{placeholder}`.
- **`response_model`** — نوع Pydantic اختياري يُستخدم للتحقق من الاستجابة. راجع
  [أجسام الطلب والاستجابات](request-response.md).
- **`use_auth`** — اضبطه على `False` لتخطّي مصادقة العميل لهذه النقطة (انظر أدناه).

## اصطلاح توقيع الدالة

تستقبل الدالة المزخرفة **النتيجة المُحلَّلة بوصفها أول وسيط بعد `self`**، ثم وسائطها الخاصة:

```python
@get("/users/{id}")
def get_user(self, response: Response, id: int):
    #              ^^^^^^^^^^^^^^^^^^  ^^^^^^^
    #              يحقنه أساس          يمرّره المستدعي
    return response.json()
```

أنت لا تمرّر الوسيط الأول بنفسك أبدًا — يحقنه أساس. وكل ما بعده جزء من توقيع دالتك العام
ويُوجَّه إلى الطلب.

## توجيه الوسائط

عند استدعاء الدالة، يفحص أساس كل وسيط من وسائطك ويوجّهه **حسب الاسم والنوع**:

| الوسيط | يُوجَّه إلى |
| --- | --- |
| اسمه يطابق `{placeholder}` في المسار | يُستبدل داخل عنوان URL |
| نموذج Pydantic (`BaseModel`) أو قائمة منها | جسم الطلب بصيغة JSON |
| أي شيء آخر ليس `None` | وسيط استعلام |

```python
from pydantic import BaseModel
from asas import AsasClient, post, Response

class CreateUser(BaseModel):
    name: str
    email: str

class MyClient(AsasClient):
    @post("/teams/{id}/users")
    def create_user(self, response: Response, id: int, payload: CreateUser, team: str):
        return response.json()

client = MyClient(base_url="https://api.example.com")
client.create_user(
    id=42,                                                  # -> مسار URL
    payload=CreateUser(name="Ada", email="ada@x.com"),     # -> جسم JSON
    team="core",                                            # -> سلسلة الاستعلام
)
# POST https://api.example.com/teams/42/users?team=core
# body: {"name": "Ada", "email": "ada@x.com"}
```

!!! warning "يجب أن تكون الأجسام نماذج Pydantic"
    لا يُعامَل القاموس (`dict`) العادي بوصفه جسمًا — بل يتحوّل إلى وسائط استعلام. غلِّف بيانات
    الجسم في `BaseModel` لإرسالها بصيغة JSON. راجع
    [أجسام الطلب والاستجابات](request-response.md).

أي وسيط قيمته `None` يُسقَط بالكامل، ما يجعل وسائط الاستعلام الاختيارية سهلة:

```python
@get("/search")
def search(self, response: Response, q: str, page: int = None):
    return response.json()

client.search(q="asas")            # GET /search?q=asas
client.search(q="asas", page=2)    # GET /search?q=asas&page=2
```

## اصطلاح القيمة المُعادة

يفحص المزخرف ما يُعيده جسم دالتك:

- إذا أعاد الجسم `None` (مثلًا كان فارغًا، مكتوبًا فقط لأجل تحديد الأنواع)، يُعيد المزخرف
  **النتيجة المُحلَّلة** التي حقنها.
- إذا أعاد الجسم قيمةً، **تفوز قيمتك أنت** — استخدم ذلك لمعالجة النتيجة لاحقًا.

=== "جسم فارغ (إعادة النتيجة المُحلَّلة)"

    ```python
    @get("/users/{id}", response_model=User)
    def get_user(self, user: User, id: int) -> User:
        ...        # يعيد الجسم None -> يعيد أساس `user`
    ```

=== "معالجة لاحقة"

    ```python
    @get("/users/{id}")
    def get_username(self, response: Response, id: int) -> str:
        return response.json()["name"]   # تُعاد قيمتك أنت
    ```

## متزامن وغير متزامن، بمزخرف واحد

تعمل المزخرفات نفسها مع دوال `def` و`async def` معًا — يكتشف أساس دوال الكوروتين تلقائيًا
ويستخدم المسار غير المتزامن للمحرّك. لا شيء إضافي تستورده.

```python
class AsyncClient(AsasAsyncClient):
    @get("/users/{id}")
    async def get_user(self, response: Response, id: int):
        return response.json()
```

!!! note
    استدعاء نقطة نهاية `async def` على محرّك متزامن (أو العكس) يرفع `TypeError` واضحًا يخبرك
    بأي بروتوكول يفتقر إليه المحرّك.

## التحكم في المصادقة لكل نقطة نهاية

حتى عندما يملك العميل استراتيجية مصادقة عامة، يمكنك تعطيلها لنقاط نهاية عامة محدّدة عبر
`use_auth=False`:

```python
class MyClient(AsasClient):
    @get("/public-data", use_auth=False)
    def get_public(self, response: Response):
        return response.json()
```

هذا أيضًا ما تستخدمه لنقطة نهاية تسجيل الدخول التي *تنتج* رمزك — راجع مثال المصادقة أثناء
التشغيل في [العملاء](clients.md).
