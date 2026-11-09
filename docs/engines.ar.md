# المحرّكات وطبقات النقل

يفصل أساس بين *ماهية* الطلب و*كيفية* انتقاله عبر الشبكة. **المحرّك** هو طبقة النقل. تتحدّث
النواة بفئات بيانات [`Request` / `Response`](models.md) بسيطة، لذا يمكن وصل أي مكتبة HTTP عبر
تطبيق محرّك.

## بروتوكولات المحرّك

المحرّكات بروتوكولات `runtime_checkable` — لا توجد فئة أساسية ترثها. يطبّق المحرّك المتزامن
دالتين، ويطبّق المحرّك غير المتزامن نظيرتيهما غير المتزامنتين:

=== "SyncEngine"

    ```python
    class SyncEngine(Protocol):
        def send(self, request: Request) -> Response: ...
        def close(self) -> None: ...
    ```

=== "AsyncEngine"

    ```python
    class AsyncEngine(Protocol):
        async def asend(self, request: Request) -> Response: ...
        async def aclose(self) -> None: ...
    ```

عند استدعاء دالة مزخرفة، يتحقّق أساس من أن المحرّك يدعم الوضع الصحيح ويرفع `TypeError` واضحًا
إذا استدعيت — مثلًا — نقطة نهاية `async def` على محرّك متزامن فقط.

## عقد المحرّك

أيًّا كانت المكتبة التي يغلّفها المحرّك، عليه اتباع قاعدتين:

- **ارفع `TransportError`.** إذا لم ينتج الطلب أي استجابة (رفض اتصال، فشل DNS، انتهاء مهلة،
  …)، فالتقط استثناء المكتبة وارفع `asas.TransportError(message, request)` مع `from` الاستثناء
  الأصلي. يعتمد أساس و[الخطافات](hooks.md) والمستدعون على هذا النوع الواحد؛ وتسريب استثناء
  مكتبة يكسر العقد. (يفعل المحرّكان المرفقان ذلك مع `httpx.TransportError` و
  `requests.RequestException`.)
- **أرسل `Request.cookies`.** `request.cookies` هو `dict[str, str]` يجب إرساله كوكيز. تكتب
  استراتيجيات المصادقة مثل `APIKeyAuth` مع `APIKeyLocation.COOKIE` هناك بدلًا من بناء ترويسة
  `Cookie` خام.

وينبغي له أيضًا احترام `request.timeout` عند ضبطه، وإرسال `payload.data` (قاموس كحقول نموذج،
و`bytes` كجسم خام) و`payload.json` و`payload.files`.

## محرّك httpx المرفق

`HTTPXSyncEngine` و`HTTPXAsyncEngine` هما التطبيقان المرجعيان والافتراضيان عند عدم تمرير
محرّك. ينشئان عميل `httpx` الأساسي بكسل (lazily) ويمرّران أي وسائط `**kwargs` للمُنشئ إليه. تُبنى الطلبات عبر عميل `httpx`، فتنطبق إعداداته
الافتراضية (`headers` و`timeout` و`cookies` …)، ويتجاوز `timeout=` الخاص بنقطة النهاية
القيمة الافتراضية للعميل.

```python
from asas import AsasClient, HTTPXSyncEngine

# These two clients are equivalent:
client = AsasClient(base_url="https://api.example.com", timeout=10.0)
client = AsasClient(
    base_url="https://api.example.com",
    engine=HTTPXSyncEngine(timeout=10.0),
)
```

تمرير المحرّك صراحةً مفيد عندما تريد ضبطه في مكان واحد. وإن شاركت محرّكًا واحدًا بين عدّة
عملاء، فتذكّر أن إغلاق أي عميل يغلق المحرّك — راجع [العملاء](clients.md).

## محرّك requests المرفق (إضافة اختيارية)

يشحن أساس أيضًا محرّكًا مبنيًا على [`requests`](https://requests.readthedocs.io/). ثبّته عبر
إضافة `requests`:

```bash
pip install "asas-py[requests]"
```

يبقى `httpx` المحرّكَ الافتراضيَ الذي يشحنه `asas-py`؛ أما محرّك `requests` فهو بديل اختياري
تختاره لكل عميل على حدة. استورده من وحدته الخاصة (لا يستورده مستوى الحزمة الأعلى إطلاقًا)
ومرّره عبر `engine=`:

```python
from asas import AsasClient
from asas.engines.requests import RequestsSyncEngine

client = AsasClient(base_url="https://api.example.com", engine=RequestsSyncEngine())
```

ينشئ جلسة `requests.Session` بتراخٍ. وعلى خلاف محرّك `httpx` لا يأخذ وسائط في مُنشئه، لأن
`requests.Session()` لا يقبل أيًّا منها. اضبط الجلسة عبر خصائصها بدلًا من ذلك، مثل
`engine.session.headers.update({"X-App": "demo"})`. وهو يدعم أيضًا أجسام JSON والبيانات الخام
`data` والملفات `files` ووسائط الاستعلام والكوكيز والترويسات المخصّصة عبر [`Payload`](models.md) نفسه (ويُرسَل `files` مع `data` معًا
بوصفهما multipart)، ويرفع `TransportError` عند فشل `requests`.

!!! warning "متزامن فقط"
    لا تدعم مكتبة `requests` غير المتزامن أصلاً، لذا فإن محرّك `requests` **متزامن فقط** —
    لا يوجد `RequestsAsyncEngine`. استخدمه مع `AsasClient` (وليس `AsasAsyncClient`). إن
    استدعت نقطة نهاية غير متزامنة على عميل يعتمد هذا المحرّك، يُرفع `TypeError` يوضّح أنه
    متزامن فقط؛ انتقل إلى `AsasClient` أو استخدم محرّك `httpx` (`HTTPXAsyncEngine`) للعمل
    غير المتزامن.

## كتابة محرّك مخصّص

لدعم طبقة نقل أخرى (`aiohttp`، `urllib`، بديل اختبار في الذاكرة، …)، طبّق البروتوكول
وحوِّل من وإلى `asas.core.models`، واتبع عقد المحرّك أعلاه. لا شيء آخر في الإطار
يحتاج إلى تغيير.
(محرّك `requests` مرفق بالفعل — راجع [أعلاه](#محرك-requests-المرفق-إضافة-اختيارية)؛ لست بحاجة إلى كتابته
بنفسك.)

```python
import requests
from asas import TransportError
from asas.core.models import Request, Response

class RequestsEngine:
    def __init__(self) -> None:
        self.session = requests.Session()

    def send(self, request: Request) -> Response:
        payload = request.payload
        try:
            resp = self.session.request(
                method=request.method,
                url=request.url,
                params=request.params,
                headers=request.headers,
                cookies=request.cookies,
                timeout=request.timeout,
                json=payload.json if payload else None,
            )
        except requests.RequestException as exc:
            raise TransportError(str(exc), request) from exc
        return Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.content,
            text=resp.text,
        )

    def close(self) -> None:
        self.session.close()
```

استخدمه بتمرير نسخة منه عبر `engine=`:

```python
from asas import AsasClient

client = AsasClient(base_url="https://api.example.com", engine=RequestsEngine())
```

!!! tip "الاختبار دون شبكة"
    المحرّك المخصّص الذي يعيد كائنات `Response` جاهزة هو أبسط طريقة لاختبار عميل وحدةً. تُحاكي
    مجموعة اختبارات أساس نفسها محرّك `httpx` بـ
    [`respx`](https://lundberg.github.io/respx/).

!!! note "`**kwargs` تضبط المحرّك الافتراضي فقط"
    تمرير `**kwargs` من العميل يستهدف محرّك `httpx` المرفق. أما المحرّك المخصّص فينبغي ضبطه
    عبر مُنشئه الخاص قبل تمريره.
