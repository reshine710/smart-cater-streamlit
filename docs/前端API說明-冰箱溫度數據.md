# 冰箱溫度數據 API 說明文件

## 一、概述

本文檔說明如何透過 API 取得機台冰箱溫度相關數據。系統提供以下功能：

1. **取得機台當前冰箱溫度**：從機台詳細資訊中取得
2. **查詢冰箱溫度歷史記錄**：查詢指定時間範圍的溫度歷史資料
3. **機台回報冰箱溫度**：透過狀態事件 API 更新冰箱溫度

---

## 二、API 端點說明

### 2.1 取得機台當前冰箱溫度

透過機台詳細資訊 API 取得機台當前冰箱溫度。

#### 請求

```http
GET /api/v1/machines/{machine_id}
Authorization: Bearer {token}
```

#### 路徑參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `machine_id` | integer | 是 | 機台 ID |

#### 回應範例

```json
{
  "id": 1,
  "machine_code": "SC-NCU-001",
  "name": "科技園區管理中心門口智慧餐機",
  "location": {
    "id": 1,
    "name": "科技園區管理中心"
  },
  "ip_address": "192.168.1.101",
  "status": "online",
  "firmware_version": "v2.2.0",
  "hardware_version": "HW-v1.2",
  "temperature": 25.5,
  "humidity": 60.0,
  "fridge_temp": 4.12,
  "max_capacity": 36,
  "last_online": "2025-01-15T10:30:00+08:00",
  "created_at": "2024-01-01T00:00:00+08:00",
  "updated_at": "2025-01-15T10:30:00+08:00",
  "current_menus": [],
  "current_fault_code": null
}
```

#### 回應欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `fridge_temp` | float \| null | 冰箱當前溫度（°C），範圍：-30°C ~ 20°C。如果為 `null`，表示機台尚未回報溫度或已逾時 |

#### 狀態碼

- `200 OK`：成功取得機台資訊
- `404 Not Found`：機台不存在
- `401 Unauthorized`：未授權

---

### 2.2 查詢冰箱溫度歷史記錄

查詢指定機台在特定時間範圍內的冰箱溫度歷史記錄。

#### 請求

```http
GET /api/v1/machines/{machine_id}/fridge-temperature/history
Authorization: Bearer {token}
```

#### 路徑參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `machine_id` | integer | 是 | 機台 ID |

#### 查詢參數

| 參數 | 類型 | 必填 | 預設值 | 說明 |
|------|------|------|--------|------|
| `start_date` | string | 否 | 無限制 | 開始日期，格式：`YYYY-MM-DD` |
| `end_date` | string | 否 | 無限制 | 結束日期，格式：`YYYY-MM-DD` |
| `limit` | integer | 否 | 1000 | 最大記錄數，範圍：1 ~ 10000 |

#### 請求範例

```http
GET /api/v1/machines/1/fridge-temperature/history?start_date=2025-01-01&end_date=2025-01-31&limit=500
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 回應範例

```json
{
  "machine_id": 1,
  "machine_code": "SC-NCU-001",
  "machine_name": "科技園區管理中心門口智慧餐機",
  "records": [
    {
      "id": 12345,
      "machine_id": 1,
      "fridge_temp": 4.12,
      "recorded_at": "2025-01-15T10:30:00+08:00",
      "created_at": "2025-01-15T10:30:00+08:00"
    },
    {
      "id": 12344,
      "machine_id": 1,
      "fridge_temp": 4.08,
      "recorded_at": "2025-01-15T10:15:00+08:00",
      "created_at": "2025-01-15T10:15:00+08:00"
    },
    {
      "id": 12343,
      "machine_id": 1,
      "fridge_temp": 4.15,
      "recorded_at": "2025-01-15T10:00:00+08:00",
      "created_at": "2025-01-15T10:00:00+08:00"
    }
  ],
  "total": 3,
  "start_date": "2025-01-01T00:00:00+08:00",
  "end_date": "2025-01-31T23:59:59+08:00"
}
```

#### 回應欄位說明

| 欄位 | 類型 | 說明 |
|------|------|------|
| `machine_id` | integer | 機台 ID |
| `machine_code` | string | 機台代碼 |
| `machine_name` | string | 機台名稱 |
| `records` | array | 溫度記錄列表，按時間倒序排列（最新的在前） |
| `records[].id` | integer | 記錄 ID |
| `records[].machine_id` | integer | 機台 ID |
| `records[].fridge_temp` | float | 冰箱溫度（°C） |
| `records[].recorded_at` | datetime | 記錄時間（ISO 8601 格式，時區：Asia/Taipei） |
| `records[].created_at` | datetime | 建立時間 |
| `total` | integer | 返回的記錄總數 |
| `start_date` | datetime \| null | 查詢開始日期（如果提供） |
| `end_date` | datetime \| null | 查詢結束日期（如果提供） |

#### 狀態碼

- `200 OK`：成功取得歷史記錄
- `400 Bad Request`：日期格式錯誤
- `404 Not Found`：機台不存在
- `401 Unauthorized`：未授權

#### 注意事項

1. **時間範圍**：如果不提供 `start_date` 和 `end_date`，會返回所有歷史記錄（受 `limit` 限制）
2. **日期格式**：日期參數必須為 `YYYY-MM-DD` 格式（例如：`2025-01-15`）
3. **時間排序**：記錄按 `recorded_at` 倒序排列（最新的在前）
4. **記錄頻率**：系統每 15 分鐘自動儲存一次溫度記錄
5. **資料保留**：歷史記錄會持續累積，建議使用日期範圍查詢以提高效能

---

### 2.3 機台回報冰箱溫度（狀態事件 API）

機台可透過狀態事件 API 回報當前冰箱溫度，系統會自動更新機台的 `fridge_temp` 欄位。

#### 請求

```http
POST /api/v1/machines/{machine_code}/status-events
Content-Type: application/json
```

#### 路徑參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `machine_code` | string | 是 | 機台代碼（例如：`SC-NCU-001`） |

#### 請求 Body

```json
{
  "fault_code": 0,
  "fridge_temp": 4.12,
  "timestamp": "2025-01-15T10:30:00Z",
  "message": "機台 alive 訊號",
  "metadata": {
    "temperature": 25.5,
    "humidity": 60.0
  }
}
```

#### 請求欄位說明

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `fault_code` | integer | 是 | 故障碼（0: alive 訊號, 1: 上線, 9: 離線, 10~99: 故障） |
| `fridge_temp` | float \| null | 否 | 冰箱溫度（°C），範圍：-30°C ~ 20°C |
| `timestamp` | datetime | 否 | 事件時間（ISO 8601 格式，預設為伺服器時間） |
| `message` | string | 否 | 事件訊息 |
| `metadata` | object | 否 | 額外的元數據 |

#### 回應範例

```json
{
  "machine_code": "SC-NCU-001",
  "machine_name": "科技園區管理中心門口智慧餐機",
  "ip_address": "192.168.1.101",
  "status": "online",
  "fault_code": null,
  "status_msg": null,
  "last_online": "2025-01-15T10:30:00+08:00",
  "fridge_temp": 4.12,
  "updated_at": "2025-01-15T10:30:00+08:00",
  "current_menus": [],
  "restock_info": []
}
```

#### 狀態碼

- `200 OK`：成功處理狀態事件
- `400 Bad Request`：請求資料驗證失敗（例如：`fridge_temp` 超出範圍）
- `404 Not Found`：機台不存在
- `401 Unauthorized`：未授權（如果啟用認證）

#### 注意事項

1. **溫度驗證**：如果 `fridge_temp` 超出 -30°C ~ 20°C 範圍，請求會被拒絕（400 Bad Request）
2. **自動更新**：當 `fridge_temp` 提供時，系統會自動更新機台的當前冰箱溫度
3. **無需認證**：此端點通常不需要認證，由機台直接調用

---

## 三、使用範例

### 3.1 JavaScript/TypeScript 範例

#### 取得機台當前冰箱溫度

```typescript
async function getMachineFridgeTemp(machineId: number, token: string) {
  const response = await fetch(`/api/v1/machines/${machineId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const machine = await response.json();
  return machine.fridge_temp; // 可能為 null
}
```

#### 查詢溫度歷史記錄

```typescript
interface FridgeTemperatureRecord {
  id: number;
  machine_id: number;
  fridge_temp: number;
  recorded_at: string;
  created_at: string;
}

interface FridgeTemperatureHistoryResponse {
  machine_id: number;
  machine_code: string;
  machine_name: string;
  records: FridgeTemperatureRecord[];
  total: number;
  start_date: string | null;
  end_date: string | null;
}

async function getFridgeTemperatureHistory(
  machineId: number,
  startDate?: string,
  endDate?: string,
  limit: number = 1000,
  token: string
): Promise<FridgeTemperatureHistoryResponse> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  params.append('limit', limit.toString());

  const response = await fetch(
    `/api/v1/machines/${machineId}/fridge-temperature/history?${params.toString()}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// 使用範例
const history = await getFridgeTemperatureHistory(
  1,
  '2025-01-01',
  '2025-01-31',
  500,
  token
);

console.log(`共取得 ${history.total} 筆溫度記錄`);
history.records.forEach(record => {
  console.log(`${record.recorded_at}: ${record.fridge_temp}°C`);
});
```

#### 機台回報冰箱溫度

```typescript
async function reportFridgeTemperature(
  machineCode: string,
  fridgeTemp: number
): Promise<void> {
  const response = await fetch(`/api/v1/machines/${machineCode}/status-events`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      fault_code: 0,
      fridge_temp: fridgeTemp,
      timestamp: new Date().toISOString(),
      message: '機台 alive 訊號'
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
}
```

### 3.2 Python 範例

```python
import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"
token = "your_access_token"

# 取得機台當前冰箱溫度
def get_machine_fridge_temp(machine_id: int):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/machines/{machine_id}", headers=headers)
    response.raise_for_status()
    machine = response.json()
    return machine.get("fridge_temp")

# 查詢溫度歷史記錄
def get_fridge_temperature_history(machine_id: int, start_date=None, end_date=None, limit=1000):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(
        f"{BASE_URL}/machines/{machine_id}/fridge-temperature/history",
        headers=headers,
        params=params
    )
    response.raise_for_status()
    return response.json()

# 使用範例
machine_id = 1
fridge_temp = get_machine_fridge_temp(machine_id)
print(f"當前冰箱溫度: {fridge_temp}°C" if fridge_temp else "尚未回報溫度")

# 查詢過去7天的歷史記錄
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

history = get_fridge_temperature_history(
    machine_id,
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d"),
    limit=500
)

print(f"共取得 {history['total']} 筆記錄")
for record in history['records']:
    print(f"{record['recorded_at']}: {record['fridge_temp']}°C")
```

---

## 四、資料格式說明

### 4.1 溫度範圍

- **有效範圍**：-30°C ~ 20°C
- **資料類型**：`float`（浮點數）
- **可為 null**：是（表示尚未回報或已逾時）

### 4.2 時間格式

所有時間欄位均使用 ISO 8601 格式，時區為 `Asia/Taipei`（UTC+8）。

範例：
- `2025-01-15T10:30:00+08:00`
- `2025-01-15T10:30:00Z`（UTC 時間，系統會自動轉換）

### 4.3 日期查詢格式

查詢參數中的日期格式為：`YYYY-MM-DD`

範例：
- `2025-01-15`
- `2025-01-31`

---

## 五、錯誤處理

### 5.1 常見錯誤碼

| 狀態碼 | 說明 | 處理方式 |
|--------|------|----------|
| `400 Bad Request` | 請求參數錯誤（日期格式錯誤、溫度超出範圍等） | 檢查請求參數格式和範圍 |
| `401 Unauthorized` | 未授權 | 檢查 token 是否有效 |
| `404 Not Found` | 機台不存在 | 檢查機台 ID 是否正確 |
| `500 Internal Server Error` | 伺服器內部錯誤 | 聯繫後端開發人員 |

### 5.2 錯誤回應格式

```json
{
  "detail": "錯誤訊息說明"
}
```

範例：

```json
{
  "detail": "start_date 格式錯誤，應為 YYYY-MM-DD"
}
```

---

## 六、最佳實踐

### 6.1 效能優化

1. **使用日期範圍查詢**：避免查詢所有歷史記錄，使用 `start_date` 和 `end_date` 限制查詢範圍
2. **適當設定 limit**：根據實際需求設定 `limit`，避免一次載入過多資料
3. **分頁載入**：如果資料量大，考慮在前端實作分頁或虛擬滾動

### 6.2 資料展示建議

1. **即時溫度顯示**：使用機台詳細資訊 API 取得當前溫度，用於即時顯示
2. **歷史趨勢圖表**：使用歷史記錄 API 繪製溫度趨勢圖
3. **異常警示**：監控溫度是否超出正常範圍（建議：2°C ~ 6°C）
4. **空值處理**：當 `fridge_temp` 為 `null` 時，顯示「尚未回報」或「資料未取得」

### 6.3 輪詢策略

如果需要在儀表板顯示即時溫度：

1. **即時顯示**：每 30 秒 ~ 1 分鐘輪詢一次機台詳細資訊 API
2. **歷史更新**：每 5 ~ 15 分鐘查詢一次歷史記錄（視需求而定）

---

## 七、FAQ

### Q1: 為什麼有些機台的 `fridge_temp` 為 `null`？

**A**: 可能原因：
- 機台尚未回報過冰箱溫度
- 機台超過 5 分鐘未更新溫度，系統會將溫度重置為 `null`

### Q2: 歷史記錄的更新頻率是多少？

**A**: 系統每 15 分鐘自動儲存一次所有在線機台的冰箱溫度到歷史表。

### Q3: 可以查詢所有機台的溫度嗎？

**A**: 目前沒有批量查詢 API，需要逐一查詢每個機台的溫度。可以使用機台列表 API 取得所有機台 ID，然後批量查詢。

### Q4: 溫度資料會保留多久？

**A**: 目前沒有自動清理機制，歷史記錄會持續累積。建議定期清理舊資料（可與後端協調）。

---

## 八、更新記錄

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.0 | 2025-01-15 | 初版發布，包含基本 API 說明 |

---

## 九、聯絡資訊

如有問題或建議，請聯繫後端開發團隊。

