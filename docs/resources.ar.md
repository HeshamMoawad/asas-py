# الموارد والترقيم الصفحي

**المورد** (resource) يجمّع نقاط النهاية الخاصة بنوع واحد من السجلّات (المستخدمون، الطلبات،
…) ويربطها بعميل. صرّح بـ `path` و`model` اختياري، فتحصل على عمليات CRUD الخمس **و** الترقيم
الصفحي الكسول مجّانًا — مع بقاء قدرتك على إضافة نقاط نهاية مخصّصة بالمزخرفات المعتادة.

```python
from pydantic import BaseModel
from asas import AsasClient, AsasResource

class User(BaseModel):
    id: int
    name: str

class Users(AsasResource):
    path = "/users"
    model = User

class MyClient(AsasClient):
    users = Users()          # اربط المورد بالعميل

client = MyClient(base_url="https://api.example.com")
client.users.get(1)          # -> User(id=1, name="...")
```

يُربَط المورد بعميله عند الوصول إليه، فيتشارك تلقائيًا `base_url` و`engine` و`auth` الخاصة
بالعميل — بما في ذلك [تجديد الرمز](authentication.md) عند `401`.

## عمليات CRUD المُولَّدة

مع ضبط `path` و`model`، يكشف المورد المتزامن (`AsasResource`) عن:

| الدالة | الطلب | تُعيد |
| --- | --- | --- |
| `list(**params)` | `GET /users` | `list[model]` (صفحة واحدة) |
| `get(id)` | `GET /users/{id}` | `model` |
| `create(obj)` | `POST /users` | `model` |
| `update(id, obj)` | `PUT /users/{id}` | `model` |
| `delete(id)` | `DELETE /users/{id}` | `Response` |

```python
client.users.list(active=True)               # GET /users?active=True
user = client.users.create(User(id=0, name="Ada"))
user = client.users.update(user.id, user)
client.users.delete(user.id)
```

تقبل `create` و`update` نموذج Pydantic (يُرسَل بوصفه جسم JSON)؛ ويُتحقَّق من الاستجابات
وتُحوَّل إلى `model`. وإذا حذفت `model`، تعود النتائج بصيغة JSON خام.

!!! note "`path` مطلوب لـ CRUD"
    استدعاء دالة CRUD أو التكرار دون `path` يرفع `ValueError` واضحًا. أما المورد الذي يحوي
    دوالًا مزخرفة مخصّصة فقط فلا يحتاج إليه.

## نقاط النهاية المخصّصة

أي شيء خارج CRUD العادي ما هو إلا دالة مزخرفة على الفئة نفسها — تمامًا كما على العميل (راجع
[التوجيه والوسائط](routing.md)):

```python
from typing import List

class Users(AsasResource):
    path = "/users"
    model = User

    @get("/users/{id}/roles", response_model=List[Role])
    def roles(self, roles: List[Role], id: int) -> List[Role]:
        return roles

client.users.roles(id=1)     # GET /users/1/roles
```

## التكرار الكسول على كل السجلّات

يمرّ تكرار المورد على **كل الصفحات**، ويجلب كلّ صفحة عند الطلب — فلا تكتب حلقة الصفحات بنفسك
أبدًا:

```python
for user in client.users:        # يجلب الصفحة 1 ثم 2 … عند الحاجة
    print(user.name)
```

وهو كسول: تُطلَب الصفحات فقط بقدر ما تستهلك من سجلّات، لذا فإن التوقّف مبكّرًا يوقف الجلب
أيضًا.

```python
# تُطلَب فقط الصفحات اللازمة لأول 10 سجلّات.
first_ten = [u for _, u in zip(range(10), client.users)]
```

استخدم `iterate(**params)` لتمرير وسائط استعلام إلى التكرار:

```python
for user in client.users.iterate(active=True):
    ...
```

## أنماط الترقيم الصفحي

اضبط `paginator` على المورد ليطابق طريقة ترقيم واجهتك. الافتراضي هو الترقيم برقم الصفحة؛ وكل
الأنماط تتشارك الحلقة الكسولة نفسها.

=== "رقم الصفحة"

    ```python
    from asas import PageNumberPaginator

    class Users(AsasResource):
        path = "/users"
        model = User
        paginator = PageNumberPaginator(page_param="page", size_param="per_page",
                                        page_size=100)
    # GET /users?page=1&per_page=100 ثم page=2 … حتى صفحة قصيرة.
    ```

=== "الإزاحة / الحد"

    ```python
    from asas import OffsetPaginator

    class Users(AsasResource):
        path = "/users"
        model = User
        paginator = OffsetPaginator(offset_param="offset", limit_param="limit", limit=100)
    # GET /users?offset=0&limit=100 ثم offset=100 … حتى صفحة قصيرة.
    ```

=== "المؤشّر / الرمز"

    ```python
    from asas import CursorPaginator

    class Users(AsasResource):
        path = "/users"
        model = User
        paginator = CursorPaginator(cursor_param="cursor", next_key="meta.next_cursor")
    # يقرأ المؤشّر التالي من جسم الاستجابة (تُسمح المسارات المنقّطة)
    # ويعيد إرساله بـ ?cursor=… ؛ ويتوقّف عند غيابه.
    ```

=== "ترويسة Link"

    ```python
    from asas import LinkHeaderPaginator

    class Users(AsasResource):
        path = "/users"
        model = User
        paginator = LinkHeaderPaginator()
    # يتبع ترويسة RFC 5988  Link: <…>; rel="next"  حتى لا تبقى واحدة.
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

يعكس `AsasAsyncResource` المورد المتزامن من أجل `AsasAsyncClient`. دوال CRUD قابلة للانتظار
بـ `await`، والتكرار يستخدم `async for`:

```python
from asas import AsasAsyncClient, AsasAsyncResource

class Users(AsasAsyncResource):
    path = "/users"
    model = User

class MyClient(AsasAsyncClient):
    users = Users()

async def main():
    client = MyClient(base_url="https://api.example.com")
    user = await client.users.get(1)
    async for user in client.users:      # كسول، صفحةً صفحة
        print(user.name)
    await client.engine.aclose()
```
