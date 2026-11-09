# النماذج الأساسية

في قلب أساس ثلاث فئات بيانات بسيطة في `asas.core.models`: `Request` و`Response` و`Payload`.
لا تعرف هذه الفئات شيئًا عن `httpx` أو أي طبقة نقل بعينها — فهي اللغة المشتركة التي تتحدّث بها
كل الطبقات، وهذا تحديدًا ما يتيح استبدال [المحرّكات](engines.md) و
[استراتيجيات المصادقة](authentication.md) بحرّية.

```
@get method  →  Request  →  auth.apply()  →  engine.send()  →  Response  →  parsed return value
```

## Request

الطلب المستقلّ عن النقل الذي تعدّله استراتيجيات المصادقة وترسله المحرّكات.

```python
@dataclass
class Request:
    method: str
    url: str
    params: dict[str, Any] | None = None
    headers: dict[str, str] = {}
    cookies: dict[str, str] = {}
    payload: Payload | None = None
    timeout: float | None = None
```

| الحقل | المعنى |
| --- | --- |
| `method` | دالة HTTP، مثل `"GET"` |
| `url` | عنوان URL المبني بالكامل (`base_url` + المسار المُحلّ) |
| `params` | وسائط الاستعلام |
| `headers` | ترويسات الطلب — حيث تكتب معظم استراتيجيات المصادقة |
| `cookies` | الكوكيز المراد إرسالها؛ على المحرّكات إرسالها (`APIKeyAuth` في كوكي تكتب هنا) |
| `payload` | جسم الطلب، إن وُجد (راجع `Payload` أدناه) |
| `timeout` | مهلة اختيارية لكل طلب |

تتلقّى دالة `Auth.apply` كائن `Request`، وتعدّل `headers` أو `cookies` أو `params` فيه، ثم تعيده.

## Response

الاستجابة المستقلّة عن النقل التي ينتجها محرّكك. يحلّلها أساس بحسب تعليق نوع القيمة المُعادة لنقطة النهاية.

```python
@dataclass
class Response:
    status_code: int
    headers: dict[str, str]
    content: bytes
    text: str

    def json(self) -> Any:
        ...
```

| العضو | المعنى |
| --- | --- |
| `status_code` | رمز حالة HTTP |
| `headers` | ترويسات الاستجابة |
| `content` | جسم الاستجابة الخام بصيغة `bytes` |
| `text` | جسم الاستجابة مُفكّك الترميز إلى `str` |
| `json()` | تحليل `content` بوصفه JSON |

عندما تكون نقطة النهاية مُعلَّقة بـ `-> Response`، يكون هذا الكائن هو ما يعيده النداء —
استدعِ `response.json()` لقراءة الجسم. راجع [أجسام الطلب والاستجابات](request-response.md).

## Payload

حاوية عامة لبيانات الطلب، محمولة على `Request.payload`.

```python
@dataclass
class Payload:
    data: dict[str, Any] | bytes | None = None
    json: Any = None
    files: dict[str, Any] | None = None
    headers: dict[str, str] = {}
```

| الحقل | المعنى |
| --- | --- |
| `data` | حقول نموذج (`dict`) أو جسم خام (`bytes`) |
| `json` | جسم JSON بأي شكل (كائن أو مصفوفة أو قيمة مفردة) — وهو ما تُفرَّغ إليه النماذج |
| `files` | رفع الملفّات، يُرسَل multipart مع أي `data` نموذجية |
| `headers` | ترويسات خاصة بالجسم |

عندما تمرّر نموذج Pydantic إلى نقطة نهاية، يُفرّغه أساس (بصيغة آمنة لـ JSON وبحسب الاسم
المستعار) ويخزّن الناتج في `Payload.json`؛ أما وسائط `Form` و`File` فتملأ `data` و`files`. راجع
[أجسام الطلب والاستجابات](request-response.md) لمعرفة كيفية عمل هذا التوجيه.

!!! note "نادرًا ما تبني هذه بنفسك"
    يبني أساس `Request` و`Payload` نيابةً عنك من استدعاء دالتك، وتبني المحرّكات `Response`.
    تتعامل مع هذه الأنواع مباشرةً بصورة رئيسية عند كتابة
    [محرّك مخصّص](engines.md) أو [استراتيجية مصادقة مخصّصة](authentication.md).
