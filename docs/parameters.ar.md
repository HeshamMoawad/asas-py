# الوسائط

افتراضيًا يستنتج أساس وجهة كل وسيط. وعندما تحتاج إلى تحكّم — ترويسة أو كوكي أو حقل نموذج أو
رفع ملف أو اسم على الشبكة ليس معرّف بايثون صالحًا — غلِّف تعليق النوع بـ `Annotated[...]` مع
**علامة** (marker).

```python
from typing import Annotated

from pydantic import BaseModel

from asas import AsasClient, Header, Query, get


class User(BaseModel):
    id: int
    name: str


class Users(AsasClient):
    @get("/users/{id}")
    def get_user(
        self,
        id: int,
        expand: Annotated[str | None, Query(alias="x-expand")] = None,
        trace: Annotated[str | None, Header("X-Trace")] = None,
    ) -> User:
        raise NotImplementedError
```

## العلامات

| العلامة | الوجهة | ملاحظات |
| --- | --- | --- |
| `Path(alias=None)` | مقطع في عنوان URL | تُرمَّز القيمة بنسبة مئوية عبر `quote(str(v), safe="")` |
| `Query(alias=None)` | سلسلة الاستعلام | القائمة أو الصف تصبح مفاتيح مكرّرة (`?tag=a&tag=b`) |
| `Header(alias=None)` | ترويسات الطلب | الاسم الافتراضي: `x_trace` يصبح `X-Trace` |
| `Cookie(alias=None)` | `Request.cookies` | |
| `Body(exclude_unset=False, exclude_none=False)` | جسم JSON | واحدة على الأكثر لكل نقطة نهاية |
| `Form(alias=None)` | جسم مُرمَّز كنموذج | يُسمح بأي عدد |
| `File(alias=None)` | جسم متعدد الأجزاء (multipart) | `bytes` أو كائن ملف ثنائي أو `(filename, content, content_type)` |

يحدّد `alias` الاسم المستخدم فعليًا على الشبكة. يمكن تمرير اسم `Header` المستعار موضعيًا
(`Header("X-Trace")`)؛ وكل وسيط آخر مفتاحي فقط. ولا يملك `Body` اسمًا مستعارًا.

```python
from typing import Annotated

from asas import AsasClient, Cookie, Header, Query, get


class Api(AsasClient):
    @get("/items")
    def list_items(
        self,
        tags: list[str],
        sort_by: Annotated[str, Query(alias="sort-by")] = "name",
        session: Annotated[str | None, Cookie()] = None,
        request_id: Annotated[str | None, Header()] = None,   # sent as Request-Id
    ) -> list[dict]:
        raise NotImplementedError
```

!!! note "موضع العلامة"
    يقرأ أساس العلامة من `Annotated[T, Marker()]`، أو من اتحاد يجمع `None` وعضوًا واحدًا من
    `Annotated[...]`. لذا تعمل الصيغتان `Annotated[str | None, Query()]` و`Annotated[str, Query()] | None`،
    ونوع الوسيط في الحالتين `str | None`. ويغلّف Python 3.10 الوسائط التي قيمتها الافتراضية `None`
    في `Optional[...]`، وأساس يتعامل مع ذلك أيضًا.

## الاستنتاج دون علامة

عندما لا يملك الوسيط علامة، يحسم أساس الأمر من تعليق النوع وقت الزخرفة:

1. الاسم يطابق `{placeholder}` في المسار: **`Path`**.
2. التعليق (بتجاهل `Optional`) هو صنف فرعي من `BaseModel` أو `list[BaseModel]` أو
   `dict` / `dict[...]`: **`Body`**.
3. أي شيء آخر: **`Query`**.

الوسيط الذي له علامة صريحة غير `Path` لا يملأ أبدًا `{placeholder}` يحمل الاسم نفسه — بل يذهب
إلى حيث تقول علامته، ويحتاج عندها المتغيّر النائب إلى وسيط `Path` خاص به.

## التسلسل

تُفرَّغ كل قيمة عبر `TypeAdapter` من Pydantic مبني من تعليق نوعها، بوضع JSON وبحسب الاسم
المستعار. وهذا يجعل `datetime` و`date` و`UUID` و`Decimal` والتعدادات وحقول النماذج ذات
الأسماء المستعارة تعمل في كل موضع، مثلًا:

```python
from datetime import datetime
from uuid import UUID

from asas import AsasClient, get


class Api(AsasClient):
    @get("/orders/{order_id}")
    def get_order(self, order_id: UUID, since: datetime | None = None) -> dict:
        raise NotImplementedError
```

- يلتزم `Body` أيضًا بـ `exclude_unset` و`exclude_none` من علامته.
- تُحوَّل القيم القياسية في المسار والاستعلام والترويسات والكوكيز والنموذج إلى `str`؛
  وتصبح القيم المنطقية `"true"` / `"false"`.
- تُسقَط `None` من الاستعلام والترويسات والكوكيز والنموذج. أما قيمة **المسار** `None` فترفع
  `ValueError` وقت الاستدعاء.
- حقول `Form` وحدها تنتج جسمًا مُرمَّزًا كنموذج؛ و`Form` مع `File` تنتج جسمًا واحدًا
  متعدد الأجزاء.

## أسبقية الترويسات

عندما تُضبط الترويسة نفسها في عدّة أماكن، يفوز المصدر الأحدث (من الأدنى إلى الأعلى):

1. ترويسات العميل الافتراضية (`AsasClient(headers=...)`، وتُمرَّر إلى المحرّك)
2. وسيط `headers=` الخاص بنقطة النهاية
3. وسائط `Header()`
4. المصادقة (مثل `BearerAuth` وهي تكتب `Authorization`)

## رفع ملف مع حقل نموذج وترويسة

يمكن الجمع بين `File` و`Form` و`Header` في دالة واحدة. تُرسَل حقول النموذج والملفات معًا في
جسم واحد من نوع `multipart/form-data`:

```python
from typing import Annotated

from pydantic import BaseModel

from asas import AsasClient, File, Form, Header, post


class Document(BaseModel):
    id: int
    title: str


class Documents(AsasClient):
    @post("/documents")
    def upload(
        self,
        file: Annotated[tuple[str, bytes, str], File()],
        title: Annotated[str, Form()],
        idempotency_key: Annotated[str, Header("Idempotency-Key")],
    ) -> Document:
        raise NotImplementedError


client = Documents(base_url="https://api.example.com")
doc = client.upload(
    ("report.pdf", b"%PDF-1.7 ...", "application/pdf"),
    title="Q3 report",
    idempotency_key="b1f6c0a2",
)
```

## أخطاء التعريف

كلٌّ مما يلي يرفع `TypeError` باسم الدالة عند تصريف نقطة النهاية:

- وجود `{placeholder}` بلا وسيط مطابق (بالاسم أو بالاسم المستعار لـ `Path`).
- وسيط `Path` بلا متغيّر نائب مطابق.
- أكثر من وسيط `Body` واحد.
- الجمع بين `Body` و`Form` أو `File`.
- وسيطان يُحسمان إلى الاسم نفسه على الشبكة في الموضع نفسه.
- غياب تعليق نوع القيمة المُعادة (استخدم `-> Response` للاستجابة الخام).
- وسيط بلا تعليق نوع.
- نقطة النهاية تأخذ `*args` أو `**kwargs`.

تُصرَّف نقاط النهاية عند تعريف الفئة، لذا تظهر هذه الأخطاء وقت الاستيراد. والاستثناء الوحيد هو
نوع غير معرَّف بعد في تلك اللحظة: عندها يُؤجَّل التصريف إلى أول استدعاء (راجع
[التوجيه](routing.md)).

## `Path` و`pathlib.Path`

علامة `Path` في أساس تحمل اسم `pathlib.Path` نفسه. استوردها بـ `from asas import Path` فقط إن
لم تكن بحاجة إلى `pathlib.Path` أيضًا؛ وإلا فاكتب `import asas` واستخدم `asas.Path`:

```python
from pathlib import Path
from typing import Annotated

import asas
from asas import AsasClient, get


class Files(AsasClient):
    @get("/files/{name}")
    def stat(self, name: Annotated[str, asas.Path()]) -> dict:
        raise NotImplementedError


def save(target: Path) -> None:
    target.write_bytes(b"")
```
