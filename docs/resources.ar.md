# الموارد والترقيم الصفحي

**المورد** (resource) يجمّع نقاط النهاية الخاصة بنوع واحد من السجلّات (المستخدمون، الطلبات،
…) ويربطها بعميل. صرّح بـ `path` وبارامتر المورد بنموذجك (`AsasResource[User]`)، فتحصل على
عمليات CRUD الخمس **و** الترقيم الصفحي الكسول مجّانًا — مع بقاء قدرتك على إضافة نقاط نهاية مخصّصة بالمزخرفات المعتادة.

```python
from pydantic import BaseModel
from asas import AsasClient, AsasResource

class User(BaseModel):
    id: int
    name: str

class Users(AsasResource[User]):
    path = "/users"

class MyClient(AsasClient):
    users = Users()          # attach the resource to the client

client = MyClient(base_url="https://api.example.com")
client.users.get(1)          # typed: User
```

يُربَط المورد بعميله عند الوصول إليه، فيتشارك تلقائيًا `base_url` و`engine` و`auth` الخاصة
بالعميل — بما في ذلك [تجديد الرمز](authentication.md) عند `401`.

## نتائج مكتوبة الأنواع واستنتاج النموذج

`AsasResource` عامّ (generic) على نموذجه، فتعرف أدوات فحص الأنواع ما يعيده كل نداء CRUD:
`client.users.get(1)` هو `User`، و`client.users.list()` هو `list[User]`، والتكرار يُنتج `User`.
ويقرأ أساس وسيط النوع وقت التشغيل أيضًا: فـ `model` المستخدم في التحقق **يُستنتج** من
`AsasResource[User]`، فلا تكرّره.

- `model = ...` صريح كسمة فئة، أو الوسيط `model=` في المُنشئ، يتجاوز النموذج المستنتج.
- `AsasResource` المجرّد بلا وسيط نوع ولا `model` يعيد JSON خامًا.

```python
class Users(AsasResource[User]):
    path = "/users"

raw = AsasResource(path="/users")      # no model: raw JSON, typed as Any
```

## عمليات CRUD المُولَّدة

مع ضبط `path` (ونموذج، مستنتج أو صريح)، يكشف المورد المتزامن (`AsasResource`) عن:

| الدالة | الطلب | تُعيد |
| --- | --- | --- |
| `list(**params)` | `GET /users` | `list[User]` (صفحة واحدة) |
| `get(id)` | `GET /users/{id}` | `User` |
| `create(obj)` | `POST /users` | `User` |
| `update(id, obj)` | `PUT /users/{id}` | `User` |
| `delete(id)` | `DELETE /users/{id}` | `None` |

```python
client.users.list(active=True)               # GET /users?active=True
user = client.users.create(User(id=0, name="Ada"))
user = client.users.update(user.id, user)
client.users.delete(user.id)
```

تقبل `create` و`update` نموذج Pydantic (يُرسَل بوصفه جسم JSON، مُفرَّغًا بصيغة آمنة لـ JSON
وبحسب الاسم المستعار)؛ ويُتحقَّق من الاستجابات وتُحوَّل إلى النموذج. وبدون نموذج تعود النتائج
بصيغة JSON خام. وتُعيد `delete` القيمة `None` وترفع خطأً عند استجابة غير 2xx. ويُرمَّز `id`
ترميزًا نسبيًا كمقطع مسار واحد، فيطلب `get("a/b")` المسار `/users/a%2Fb`.

تمرّ طلبات CRUD والترقيم الصفحي عبر خط المعالجة نفسه الذي تمرّ به نقاط النهاية المزخرفة، فترفع
[أخطاءً مكتوبة الأنواع](errors.md) وتُطلق [خطافات](hooks.md) العميل. وإذا فشل التحقق من سجلّ أو
صفحة، يرفع المورد [`ResponseValidationError`](errors.md) لا `ValidationError` الخام من Pydantic.

!!! note "`path` مطلوب لـ CRUD"
    استدعاء دالة CRUD أو التكرار دون `path` يرفع `ValueError` واضحًا. أما المورد الذي يحوي
    دوالًا مزخرفة مخصّصة فقط فلا يحتاج إليه.

## نقاط النهاية المخصّصة

أي شيء خارج CRUD العادي ما هو إلا دالة مزخرفة على الفئة نفسها — تمامًا كما على العميل (راجع
[التوجيه](routing.md)):

```python
from asas import AsasResource, get

class Role(BaseModel):
    name: str

class Users(AsasResource[User]):
    path = "/users"

    @get("/users/{id}/roles")
    def roles(self, id: int) -> list[Role]:
        raise NotImplementedError

client.users.roles(1)        # GET /users/1/roles
```

## التكرار الكسول على كل السجلّات

يمرّ تكرار المورد على **كل الصفحات**، ويجلب كلّ صفحة عند الطلب — فلا تكتب حلقة الصفحات بنفسك
أبدًا:

```python
for user in client.users:        # fetches page 1, then 2, … as needed
    print(user.name)
```

وهو كسول: تُطلَب الصفحات فقط بقدر ما تستهلك من سجلّات، لذا فإن التوقّف مبكّرًا يوقف الجلب
أيضًا.

```python
# Only the pages needed for the first 10 records are ever requested.
first_ten = [u for _, u in zip(range(10), client.users)]
```

استخدم `iterate(**params)` لتمرير وسائط استعلام إلى التكرار:

```python
for user in client.users.iterate(active=True):
    ...
```

يتوقّف التكرار حين لا يجد المُرقِّم صفحة تالية. ويتوقّف كذلك حين تجيب صفحة **بعد الأولى**
بالحالة `404`، وهكذا تردّ DRF وواجهات مشابهة على صفحة بعد النهاية. هذا الـ`404` ينهي التكرار
بهدوء: لا يُرفَع خطأ ولا تُستدعى خطافات `on_error`. أمّا `404` على الصفحة الأولى فيرفع
[`NotFoundError`](errors.md)، وأي حالة أخرى غير 2xx على أي صفحة ترفع خطأً كالمعتاد.

## أنماط الترقيم الصفحي

اضبط `paginator` على المورد ليطابق طريقة ترقيم واجهتك. الافتراضي هو الترقيم برقم الصفحة؛ وكل
الأنماط تتشارك الحلقة الكسولة نفسها.

=== "رقم الصفحة"

    ```python
    from asas import PageNumberPaginator

    class Users(AsasResource[User]):
        path = "/users"
        paginator = PageNumberPaginator(page_param="page", size_param="per_page",
                                        page_size=100)
    # GET /users?page=1&per_page=100, then page=2, … until a short page.
    ```

=== "الإزاحة / الحد"

    ```python
    from asas import OffsetPaginator

    class Users(AsasResource[User]):
        path = "/users"
        paginator = OffsetPaginator(offset_param="offset", limit_param="limit", limit=100)
    # GET /users?offset=0&limit=100, then offset=100, … until a short page.
    ```

=== "المؤشّر / الرمز"

    ```python
    from asas import CursorPaginator

    class Users(AsasResource[User]):
        path = "/users"
        paginator = CursorPaginator(cursor_param="cursor", next_key="meta.next_cursor")
    # Reads the next cursor from the response body (dotted paths allowed) and
    # sends it back as ?cursor=…; stops when it is absent.
    ```

=== "ترويسة Link"

    ```python
    from asas import LinkHeaderPaginator

    class Users(AsasResource[User]):
        path = "/users"
        paginator = LinkHeaderPaginator()
    # Follows the RFC 5988  Link: <…>; rel="next"  header until there is none.
    ```

### أين تقع السجلّات في الصفحة

يعثر كل مرقِّم على قائمة السجلّات في الصفحة تلقائيًا: تُستخدم مصفوفة JSON عُليا كما هي، وإلّا
فأوّل ما يوجد من `data` / `items` / `results`. تجاوز ذلك بـ `items_key` (مسار منقّط) عندما
تضعها واجهتك في مكان آخر متداخل:

```python
paginator = PageNumberPaginator(items_key="data.records")
```

### الاستراتيجيات المخصّصة

لدعم نمط خاص، ورِث `Paginator` وطبّق `first_page` و`next_page`، مُعيدًا `PageRequest` (أو
`None` للتوقّف):

```python
from asas import Paginator, PageRequest
from asas.core.models import Response

class HeaderCountPaginator(Paginator):
    def first_page(self, params):
        page = dict(params); page["page"] = 1
        return PageRequest(params=page)

    def next_page(self, response: Response, previous: PageRequest):
        total = int(response.headers.get("X-Total-Pages", "1"))
        current = int(previous.params["page"])
        if current >= total:
            return None
        page = dict(previous.params); page["page"] = current + 1
        return PageRequest(params=page)
```

## الموارد غير المتزامنة

يعكس `AsasAsyncResource[User]` المورد المتزامن من أجل `AsasAsyncClient`. دوال CRUD قابلة للانتظار
بـ `await`، والتكرار يستخدم `async for`:

```python
from asas import AsasAsyncClient, AsasAsyncResource

class Users(AsasAsyncResource[User]):
    path = "/users"

class MyClient(AsasAsyncClient):
    users = Users()

async def main():
    async with MyClient(base_url="https://api.example.com") as client:
        user = await client.users.get(1)
        async for user in client.users:      # lazy, page by page
            print(user.name)
```
