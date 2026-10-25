# decision_service

FastAPI-сервис принятия решения, совместимый с `application_server`.

- `POST /api/v1/decisions` — принимает существующий Java `DecisionRequest`.
- Внутри преобразует данные в 12 полей исходной скоринговой карты.
- Недостающие для текущего backend данные (обороты, расходы, БКИ, оценка залога) сейчас приходят из детерминированных локальных моков — это точка замены на реальные/отдельные mock-сервисы.
- Возвращает `APPROVED`, `COUNTER_OFFER` или `REJECTED` плюс score/risk grade/rate/DTI.
- `GET /health` — healthcheck.

## Запуск

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8090 --reload
```

По умолчанию межсервисный токен: `change-me-internal-token`. Можно заменить через `INTERNAL_SERVICE_TOKEN`.
