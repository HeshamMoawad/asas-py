# أساس (Asas)

<p align="center">
  <img src="https://heshammoawad.github.io/asas-py/assets/logo-without-bg.png" alt="شعار أساس" width="300">
</p>

<p align="center"><em>إطار عمل أساس، أداء عالٍ، سهل التعلم، سريع البرمجة، جاهز للإنتاج</em></p>

---

## عن المشروع

أساس هو إطار عمل مبسّط لبناء **عملاء واجهات برمجة التطبيقات (SDKs)** عبر واجهة نظيفة تعتمد على
المزخرفات (decorators). تقوم بوراثة عميل، ثم تُعلِّم الدوال بـ `@get` / `@post` وما إلى ذلك،
ويتولّى أساس بناء الطلب والمصادقة والتحليل وإعادة المحاولة نيابةً عنك.

صُمِّم لبايثون الحديثة: دعم أصيل لـ `async`/`await` وتكامل من الدرجة الأولى مع
[Pydantic](https://docs.pydantic.dev/) للتحقق من بيانات الطلب والاستجابة.

## الهدف

الهدف الأساسي لأساس هو جعل تكامل واجهات البرمجة أكثر **بايثونية** وبساطة وقابلية للصيانة. من
خلال تجريد الإطالة المعتادة في مكتبات الطلبات التقليدية، يتيح لك أساس التركيز على بنية واضحة
وكود معبّر.

## التثبيت

```bash
pip install asas-py
```

## البداية السريعة

يوفّر أساس عملاء منفصلين للكود المتزامن وغير المتزامن. تعمل المزخرفات نفسها مع كليهما — إذ
يكتشف أساس دوال `async def` تلقائيًا.

=== "متزامن"

    ```python
    from pydantic import BaseModel

    from asas import AsasClient, get

    class User(BaseModel):
        id: int
        name: str

    class MyClient(AsasClient):
        @get("/users/{id}")
        def get_user(self, id: int) -> User: ...

    with MyClient(base_url="https://api.example.com") as client:
        user = client.get_user(1)   # typed: User
    ```

=== "غير متزامن"

    ```python
    from pydantic import BaseModel

    from asas import AsasAsyncClient, get

    class User(BaseModel):
        id: int
        name: str

    class MyAsyncClient(AsasAsyncClient):
        @get("/users/{id}")
        async def get_user(self, id: int) -> User: ...

    async def main() -> None:
        async with MyAsyncClient(base_url="https://api.example.com") as client:
            user = await client.get_user(1)   # typed: User
    ```

!!! tip "تعليق نوع القيمة المُعادة يقود كل شيء"
    جسم الدالة **لا يُنفَّذ أبدًا** — اكتب `...`. يقرأ أساس **تعليق نوع
    القيمة المُعادة** (`-> User`) ليحلّل الاستجابة ويتحقّق منها، و**الوسائط** ليبني الطلب.
    ويرى المستدعون التوقيع الذي صرّحت به تمامًا، فتفهم أدوات فحص الأنواع ومحرّرات الكود
    `client.get_user(1)`. راجع [التوجيه](routing.md) و[الوسائط](parameters.md).

!!! info "تُرقّي من 0.1؟"
    الإصدار 0.2 كاسر للتوافق. راجع [دليل الترقية](migration-0.2.md).

## أبرز المزايا

- **[العملاء](clients.md)** — عملاء متزامنون وغير متزامنين بطبقة نقل قابلة للاستبدال ومصادقة
  قابلة للتغيير أثناء التشغيل.
- **[التوجيه](routing.md)** — `@get`/`@post`/`@put`/`@delete`/`@patch`، ويقود تعليق نوع
  القيمة المُعادة تحليل الاستجابة.
- **[الوسائط](parameters.md)** — علامات `Path` و`Query` و`Header` و`Cookie` و`Body` و`Form`
  و`File`، مع أسماء مستعارة واستنتاج عند حذفها.
- **[أجسام الطلب والاستجابات](request-response.md)** — نماذج Pydantic تدخل، ونماذج مُتحقَّق
  منها تخرج، مكتوبة الأنواع من تعليق القيمة المُعادة.
- **[الأخطاء](errors.md)** — الاستجابات غير 2xx ترفع استثناءات مكتوبة الأنواع مثل
  `NotFoundError` و`RateLimitError`.
- **[الخطافات](hooks.md)** — راقب أو عدّل كل طلب واستجابة وخطأ.
- **[الموارد والترقيم الصفحي](resources.md)** — عمليات CRUD قائمة على الاصطلاح وتكرار كسول
  على كل سجلّ، دون أي كود لحلقة الصفحات.
- **[المصادقة](authentication.md)** — أساسية، وحاملة، ومفتاح API، وتجديد تلقائي،
  واستراتيجيات مركَّبة.
- **[المحرّكات وطبقات النقل](engines.md)** — نواة مستقلّة عن النقل؛ و`httpx` هو المحرّك
  المرجعي المرفق، مع محرّك `requests` اختياري عبر إضافة.
- **[الترقية إلى 0.2](migration-0.2.md)** — «قبل/بعد» لكل تغيير كاسر.
- **[النماذج الأساسية](models.md)** — فئات بيانات `Request` / `Response` / `Payload` بسيطة
  تتحدّث بها كل الطبقات.
