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

الهدف الأساسي لأساس هو جعل تكامل واجهات البرمجة أكثر **بايثونية** وأناقة وقابلية للصيانة. من
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
    from asas import AsasClient, get, Response

    class MyClient(AsasClient):
        @get("/users/{id}")
        def get_user(self, response: Response, id: int):
            return response.json()

    client = MyClient(base_url="https://api.example.com")
    user = client.get_user(id=1)
    ```

=== "غير متزامن"

    ```python
    from asas import AsasAsyncClient, get, Response

    class MyAsyncClient(AsasAsyncClient):
        @get("/users/{id}")
        async def get_user(self, response: Response, id: int):
            return response.json()

    async def main():
        client = MyAsyncClient(base_url="https://api.example.com")
        user = await client.get_user(id=1)
        await client.engine.aclose()
    ```

!!! tip "الوسيط الأول المُحقَن"
    تستقبل الدالة المزخرفة النتيجة المُحلَّلة بوصفها **أول وسيط بعد `self`** (وهو `response`
    أعلاه). أما الوسائط المتبقية — مثل `id` — فيُمرِّرها المستدعي ويُوجَّهها أساس إلى الطلب.
    راجع [التوجيه والوسائط](routing.md).

## أبرز المزايا

- **[العملاء](clients.md)** — عملاء متزامنون وغير متزامنين بطبقة نقل قابلة للاستبدال ومصادقة
  قابلة للتغيير أثناء التشغيل.
- **[التوجيه والوسائط](routing.md)** — `@get`/`@post`/`@put`/`@delete`/`@patch` مع توجيه
  تلقائي للمسار والاستعلام والجسم.
- **[أجسام الطلب والاستجابات](request-response.md)** — نماذج Pydantic تدخل، ونماذج مُتحقَّق
  منها تخرج عبر `response_model`.
- **[الموارد والترقيم الصفحي](resources.md)** — عمليات CRUD قائمة على الاصطلاح وتكرار كسول
  على كل سجلّ، دون أي كود لحلقة الصفحات.
- **[المصادقة](authentication.md)** — أساسية، وحاملة، ومفتاح API، وتجديد تلقائي،
  واستراتيجيات مركَّبة.
- **[المحرّكات وطبقات النقل](engines.md)** — نواة مستقلّة عن النقل؛ و`httpx` هو المحرّك
  المرجعي المرفق، مع محرّك `requests` اختياري عبر إضافة.
- **[النماذج الأساسية](models.md)** — فئات بيانات `Request` / `Response` / `Payload` بسيطة
  تتحدّث بها كل الطبقات.
