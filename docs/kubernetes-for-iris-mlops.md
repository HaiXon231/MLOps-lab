# Kubernetes cho project Iris MLOps

Tài liệu này giới thiệu Kubernetes từ góc nhìn của project hiện tại: một FastAPI tải model `iris-classifier@champion` từ MLflow rồi cung cấp API dự đoán. Mục tiêu là hiểu **vì sao cần Kubernetes**, **các thành phần trọng tâm**, và **cách chuyển từ Docker/Docker Compose sang Kubernetes**.

> Phạm vi học tập: chạy một cluster local bằng Minikube, kind hoặc Docker Desktop Kubernetes. Phần cuối tài liệu chỉ ra những gì phải thay đổi trước khi dùng production.

## 1. Kubernetes là gì?

Kubernetes, thường viết tắt là K8s, là nền tảng điều phối container. Docker giúp đóng gói và chạy **một container**; Kubernetes quản lý **một hệ thống gồm nhiều container** trên một hoặc nhiều máy.

Ta không ra lệnh theo kiểu “hãy chạy container này đúng một lần”. Ta khai báo trạng thái mong muốn:

```text
Tôi muốn luôn có 2 instance iris-api,
dùng image iris-api:1.0,
nhận request qua một địa chỉ ổn định,
và chỉ nhận traffic sau khi model đã tải xong.
```

Các controller của Kubernetes liên tục so sánh:

```text
Desired state (trạng thái mong muốn)
                │
                ▼
        Kubernetes controllers
                │
                ▼
Actual state (trạng thái thực tế)
```

Nếu một container chết, Kubernetes tạo container khác. Nếu đổi image từ `1.0` sang `1.1`, Kubernetes rollout phiên bản mới theo chiến lược đã khai báo.

Kubernetes không tự huấn luyện model tốt hơn, không thay thế MLflow, không tự tạo CI/CD, và không tự cung cấp monitoring hoàn chỉnh. Nó là nền tảng để vận hành các thành phần đó một cách có tổ chức.

## 2. Docker, Docker Compose và Kubernetes khác nhau thế nào?

| Công cụ | Vai trò chính | Phù hợp |
|---|---|---|
| Docker | Build image và chạy container | Một ứng dụng hoặc thử nghiệm local |
| Docker Compose | Chạy nhiều container trên một máy | Development, demo, integration test |
| Kubernetes | Điều phối workload trên cluster | Học orchestration, staging, production |

Ánh xạ gần đúng:

| Docker Compose | Kubernetes |
|---|---|
| `service` | `Deployment` và `Service` |
| `environment` | `ConfigMap` hoặc `Secret` |
| `ports` | `Service`, và có thể thêm `Ingress` |
| bind mount/volume | `PersistentVolumeClaim` |
| `depends_on` | Readiness probe, startup probe, retry logic |
| `docker compose up` | `kubectl apply -f ...` |
| `docker compose logs` | `kubectl logs` |
| `docker compose ps` | `kubectl get pods` |

Điểm quan trọng: Kubernetes không phải là “Docker Compose viết bằng YAML khác”. Kubernetes quản lý desired state, networking, rollout, scheduling, health checking, storage và quyền truy cập ở cấp cluster.

## 3. Những khái niệm Kubernetes trọng tâm

### 3.1 Cluster, control plane và worker node

Một cluster gồm:

- **Control plane**: nhận YAML/API request, lưu trạng thái cluster, lập lịch và điều khiển các resource.
- **Worker node**: máy thực sự chạy các Pod.
- **kubelet**: agent trên mỗi node, bảo đảm Pod được chạy đúng mô tả.
- **container runtime**: chạy container, thường là containerd.

Với Minikube/kind, tất cả có thể nằm trên cùng laptop. Production thường có nhiều node.

### 3.2 Pod

Pod là đơn vị triển khai nhỏ nhất. Một Pod chứa một hoặc nhiều container dùng chung network namespace và có thể dùng chung volume.

Trong project này, một Pod API có thể chứa:

```text
Pod iris-api-xxxxx
└── container iris-api
    └── uvicorn src.api:app --port 8000
```

Pod là tạm thời. Không nên phụ thuộc vào tên hoặc IP của Pod vì Pod có thể bị xóa và tạo lại với IP mới.

### 3.3 Deployment

Deployment quản lý các Pod stateless:

- Giữ đúng số lượng replica.
- Tạo lại Pod bị lỗi.
- Rolling update khi đổi image.
- Rollback về revision trước.

FastAPI phù hợp với Deployment. MLflow có thể dùng Deployment trong môi trường học tập, nhưng cần xử lý cẩn thận database và artifact storage.

### 3.4 Service

Service cung cấp DNS và địa chỉ ổn định cho một nhóm Pod.

Ví dụ, API không cần biết IP Pod MLflow. Nó gọi:

```text
http://mlflow:5000
```

DNS `mlflow` trỏ tới Service, Service chuyển request tới Pod MLflow đang healthy.

Các loại Service thường gặp:

- `ClusterIP`: chỉ truy cập trong cluster; nên dùng giữa API và MLflow.
- `NodePort`: mở một port trên node; tiện để học nhưng ít dùng trực tiếp trong production.
- `LoadBalancer`: yêu cầu cloud provider hoặc load-balancer implementation.
- `ExternalName`: ánh xạ Service tới một DNS bên ngoài.

### 3.5 ConfigMap và Secret

ConfigMap lưu cấu hình không nhạy cảm:

```text
MLFLOW_TRACKING_URI=http://mlflow:5000
MODEL_URI=models:/iris-classifier@champion
```

Secret lưu password, token hoặc credential. Không nên đặt password database trực tiếp trong Deployment YAML. Lưu ý: Secret mặc định chỉ được mã hóa base64, không đồng nghĩa với mã hóa an toàn tại rest; production cần RBAC và encryption-at-rest phù hợp.

### 3.6 PersistentVolume và PersistentVolumeClaim

Filesystem bên trong Pod là tạm thời. Nếu Pod MLflow bị tạo lại, file `mlflow.db` và model artifact sẽ mất nếu chỉ nằm trong container.

`PersistentVolumeClaim` (PVC) là yêu cầu storage bền vững:

```text
MLflow Pod
   │
   └── /mlflow-data ── PVC ── Persistent storage
                         ├── mlflow.db
                         └── mlartifacts/
```

PVC giải quyết việc dữ liệu tồn tại qua lần restart Pod. Nó không tự biến SQLite thành database chịu tải cao hoặc highly available.

### 3.7 Probe: startup, readiness và liveness

- **startupProbe**: ứng dụng đã khởi động xong chưa? Hữu ích khi API cần thời gian tải model.
- **readinessProbe**: Pod đã sẵn sàng nhận traffic chưa? Pod chưa ready sẽ bị loại khỏi Service endpoints.
- **livenessProbe**: tiến trình còn sống đúng nghĩa không? Nếu thất bại nhiều lần, kubelet restart container.

Với project này, `/health` chỉ tồn tại sau khi import app và tải model thành công, nên có thể dùng làm startup/readiness probe ban đầu.

### 3.8 Job và CronJob

- **Job** chạy một công việc đến khi hoàn thành, phù hợp với training một lần.
- **CronJob** tạo Job theo lịch, phù hợp với retraining định kỳ.

Training không nên chạy như một API Deployment luôn tồn tại. Nó là batch workload nên Job là mô hình tự nhiên hơn.

### 3.9 Ingress

Ingress định tuyến HTTP từ bên ngoài vào các Service, ví dụ:

```text
https://iris.example.com       → iris-api:8000
https://mlflow.example.com     → mlflow:5000
```

Ingress resource cần một Ingress Controller như NGINX Ingress. Local learning có thể dùng `kubectl port-forward` trước khi học Ingress.

### 3.10 Resource requests, limits và autoscaling

`requests` giúp scheduler biết Pod cần bao nhiêu CPU/RAM. `limits` giới hạn mức Pod được sử dụng.

Horizontal Pod Autoscaler (HPA) có thể thay đổi số replica API theo CPU, memory hoặc custom metrics. Tuy nhiên, scale API ML không chỉ phụ thuộc CPU; latency, request rate và thời gian inference thường là metrics hữu ích hơn.

## 4. Project Iris hiện tại gồm những gì?

### Thành phần hiện tại

```text
src/train.py
   │ train + log metrics + register model
   ▼
MLflow Tracking Server :5000
   ├── SQLite: mlflow.db
   ├── artifacts: mlartifacts/
   └── registry alias: iris-classifier@champion

src/api.py / FastAPI :8000
   └── mlflow.sklearn.load_model("models:/iris-classifier@champion")
```

### Những vấn đề đã gặp khi dùng Docker

1. MLflow lưu artifact bằng đường dẫn local của host.
2. Container API có filesystem riêng nên không thấy đường dẫn đó nếu không bind mount.
3. `host.docker.internal` cần cấu hình Host allowlist của MLflow.
4. API tải model ngay lúc import; model/MLflow chưa sẵn sàng thì container thoát.
5. `MODEL_URI` đang gán cứng trong `src/api.py`, nên environment variable chưa có tác dụng.

Kubernetes giải quyết tốt service discovery, restart, health check và cấu hình. Riêng artifact cần chọn đúng kiến trúc: API nên tải artifact qua MLflow HTTP proxy hoặc object storage, không dựa vào đường dẫn filesystem của một node.

## 5. Kiến trúc Kubernetes đề xuất để học

```text
                         ┌──────────────────────────────┐
Developer                │ Kubernetes cluster           │
                         │                              │
curl / client ──────────►│ Service iris-api            │
                         │        │                     │
                         │        ▼                     │
                         │ Deployment iris-api          │
                         │   ├── Pod API 1              │
                         │   └── Pod API 2 (tùy chọn)   │
                         │        │                     │
                         │        │ http://mlflow:5000   │
                         │        ▼                     │
                         │ Service mlflow               │
                         │        │                     │
                         │ Deployment mlflow (1 replica)│
                         │        │                     │
                         │        ▼                     │
                         │ PVC /mlflow-data             │
                         │  ├── mlflow.db               │
                         │  └── mlartifacts/            │
                         └──────────────────────────────┘
```

Khác với cách bind mount trước đây, cấu hình học tập nên để MLflow **proxy artifact qua HTTP**:

```text
API Pod → MLflow Service → MLflow Pod → PVC
```

API Pod không cần mount PVC và không cần biết model nằm ở node nào.

## 6. Kubernetes mang lại tính năng gì cho project này?

| Tính năng | Áp dụng vào Iris project |
|---|---|
| Self-healing | API crash vì lỗi tạm thời thì Pod được tạo lại |
| Service discovery | API dùng `http://mlflow:5000`, không dùng IP động |
| Load balancing | Service chia request cho nhiều replica API |
| Rolling update | Cập nhật `iris-api:1.0` lên `1.1` có kiểm soát |
| Rollback | Quay lại image cũ nếu release lỗi |
| Configuration | URI model và MLflow nằm trong ConfigMap |
| Persistent storage | DB và artifact MLflow tồn tại khi Pod restart |
| Health management | Chỉ gửi traffic khi API đã tải model |
| Batch workload | Training chạy dưới dạng Job |
| Scheduled retraining | CronJob có thể train theo lịch |
| Resource governance | Đặt requests/limits cho API và MLflow |
| Autoscaling | Tăng replica API khi tải inference tăng |

Kubernetes không tự động chuyển alias `champion`, không tự đánh giá accuracy và không quyết định model nào đủ tốt. Phần đó thuộc pipeline MLOps: train → evaluate → approval → promote alias → deploy/reload.

## 7. Chuẩn bị ứng dụng trước khi chuyển sang Kubernetes

### 7.1 Cho phép cấu hình `MODEL_URI`

Trong `src/api.py`, nên đổi:

```python
MODEL_URI = "models:/iris-classifier@champion"
```

thành:

```python
MODEL_URI = os.getenv(
    "MODEL_URI",
    "models:/iris-classifier@champion",
)
```

Nhờ đó cùng một image có thể chạy model `champion`, `challenger` hoặc một version cụ thể mà không cần build lại.

### 7.2 Tách health endpoints

Khi project lớn hơn, nên có:

- `/live`: tiến trình API còn hoạt động.
- `/ready`: model đã tải và API có thể dự đoán.

Không nên để liveness phụ thuộc lâu dài vào một dịch vụ ngoài như MLflow, vì MLflow tạm gián đoạn có thể khiến toàn bộ API Pod bị restart không cần thiết.

### 7.3 Không đặt secret trong image

Nếu sau này dùng PostgreSQL/S3/MinIO, credential phải đến từ Secret hoặc external secret manager, không ghi trong Dockerfile/Git.

### 7.4 Gắn version bất biến cho image

Nên dùng:

```text
iris-api:1.0.0
iris-api:<git-commit-sha>
```

Tránh phụ thuộc vào `latest`, vì cùng một tên có thể trỏ tới nội dung khác nhau và làm rollout khó truy vết.

## 8. Bộ manifest mẫu cho môi trường học tập

Nên tổ chức file như sau:

```text
k8s/
├── 00-namespace.yaml
├── 01-config.yaml
├── 02-mlflow-storage.yaml
├── 03-mlflow.yaml
├── 04-train-job.yaml
└── 05-api.yaml
```

Các manifest dưới đây là nền tảng để bạn tự tạo các file tương ứng.

### 8.1 Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: iris-mlops
```

Namespace nhóm các resource của project và tránh trộn lẫn với ứng dụng khác.

### 8.2 ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: iris-config
  namespace: iris-mlops
data:
  MLFLOW_TRACKING_URI: http://mlflow:5000
  MODEL_URI: models:/iris-classifier@champion
  MLFLOW_EXPERIMENT_NAME: iris-classification
```

### 8.3 PersistentVolumeClaim cho MLflow

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mlflow-data
  namespace: iris-mlops
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 2Gi
```

Local cluster thường có default StorageClass tự cấp volume. Kiểm tra bằng:

```bash
kubectl get storageclass
```

### 8.4 MLflow Deployment và Service

Nên dùng cùng major/minor version MLflow ở server, training image và API image để giảm rủi ro tương thích.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow
  namespace: iris-mlops
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mlflow
  template:
    metadata:
      labels:
        app: mlflow
    spec:
      containers:
        - name: mlflow
          image: ghcr.io/mlflow/mlflow:v3.16.1
          args:
            - mlflow
            - server
            - --backend-store-uri
            - sqlite:////mlflow-data/mlflow.db
            - --serve-artifacts
            - --artifacts-destination
            - /mlflow-data/mlartifacts
            - --host
            - 0.0.0.0
            - --port
            - "5000"
            - --allowed-hosts
            - mlflow,mlflow:5000,localhost,localhost:5000,127.0.0.1,127.0.0.1:5000
          ports:
            - name: http
              containerPort: 5000
          volumeMounts:
            - name: data
              mountPath: /mlflow-data
          readinessProbe:
            tcpSocket:
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: mlflow-data
---
apiVersion: v1
kind: Service
metadata:
  name: mlflow
  namespace: iris-mlops
spec:
  selector:
    app: mlflow
  ports:
    - name: http
      port: 5000
      targetPort: http
  type: ClusterIP
```

Hai điểm quan trọng:

1. SQLite absolute URI cần bốn dấu `/`: `sqlite:////mlflow-data/mlflow.db`.
2. Dùng `--artifacts-destination`, không dùng `--default-artifact-root`, để experiment mới có artifact URI qua MLflow proxy. Nhờ đó API không phải mount PVC.

### 8.5 Training Job

Image API hiện chứa cả `src/train.py`, nên có thể ghi đè command để dùng nó làm Job học tập:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: iris-train
  namespace: iris-mlops
spec:
  backoffLimit: 2
  template:
    metadata:
      labels:
        app: iris-train
    spec:
      restartPolicy: Never
      containers:
        - name: trainer
          image: iris-api:1.0
          imagePullPolicy: IfNotPresent
          command: ["python", "src/train.py"]
          envFrom:
            - configMapRef:
                name: iris-config
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              cpu: "1"
              memory: 1Gi
```

Job hiện đăng ký một model version nhưng chưa tự đặt alias `champion`. Sau khi Job hoàn thành, mở MLflow UI và gán alias `champion` cho version mong muốn. Trong pipeline trưởng thành hơn, bước promotion phải dựa trên metric threshold và approval policy.

### 8.6 API Deployment và Service

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: iris-api
  namespace: iris-mlops
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app: iris-api
  template:
    metadata:
      labels:
        app: iris-api
    spec:
      containers:
        - name: api
          image: iris-api:1.0
          imagePullPolicy: IfNotPresent
          envFrom:
            - configMapRef:
                name: iris-config
          ports:
            - name: http
              containerPort: 8000
          startupProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 5
            failureThreshold: 30
          readinessProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 10
            failureThreshold: 3
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
---
apiVersion: v1
kind: Service
metadata:
  name: iris-api
  namespace: iris-mlops
spec:
  selector:
    app: iris-api
  ports:
    - name: http
      port: 8000
      targetPort: http
  type: ClusterIP
```

API không mount `mlflow-data`. Nó gọi MLflow Service và tải artifact qua HTTP proxy.

## 9. Trình tự triển khai local

### Bước 1: tạo cluster

Ví dụ với Minikube:

```bash
minikube start
kubectl cluster-info
kubectl get nodes
```

Hoặc với kind:

```bash
kind create cluster --name iris-mlops
kubectl cluster-info --context kind-iris-mlops
```

Chỉ cần chọn một công cụ, không cần chạy cả hai.

### Bước 2: build và đưa image vào cluster local

```bash
docker build -t iris-api:1.0 .
```

Minikube:

```bash
minikube image load iris-api:1.0
```

kind:

```bash
kind load docker-image iris-api:1.0 --name iris-mlops
```

Production thường push image lên registry thay vì load trực tiếp.

### Bước 3: tạo namespace, config, storage và MLflow

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-config.yaml
kubectl apply -f k8s/02-mlflow-storage.yaml
kubectl apply -f k8s/03-mlflow.yaml

kubectl get pods -n iris-mlops -w
```

### Bước 4: truy cập MLflow UI

```bash
kubectl port-forward -n iris-mlops service/mlflow 5000:5000
```

Mở `http://127.0.0.1:5000`.

### Bước 5: train model

```bash
kubectl apply -f k8s/04-train-job.yaml
kubectl logs -n iris-mlops job/iris-train -f
```

Sau khi Job thành công:

```bash
kubectl get jobs -n iris-mlops
```

Vào MLflow UI, chọn version mới và đặt alias chính xác là `champion`.

### Bước 6: deploy API

```bash
kubectl apply -f k8s/05-api.yaml
kubectl rollout status deployment/iris-api -n iris-mlops
kubectl get pods,services -n iris-mlops
```

### Bước 7: gọi API

```bash
kubectl port-forward -n iris-mlops service/iris-api 8000:8000
```

Terminal khác:

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "sepal_length": 5.1,
    "sepal_width": 3.5,
    "petal_length": 1.4,
    "petal_width": 0.2
  }'
```

## 10. Các thao tác Kubernetes cần luyện tập

### Xem trạng thái

```bash
kubectl get all -n iris-mlops
kubectl get pods -n iris-mlops -o wide
kubectl describe pod -n iris-mlops <pod-name>
kubectl get events -n iris-mlops --sort-by=.metadata.creationTimestamp
```

### Xem log

```bash
kubectl logs -n iris-mlops deployment/iris-api
kubectl logs -n iris-mlops deployment/mlflow
kubectl logs -n iris-mlops <pod-name> --previous
```

`--previous` rất hữu ích khi container vừa crash và đã được restart.

### Kiểm tra DNS và networking

```bash
kubectl exec -n iris-mlops deployment/iris-api -- \
  python -c "import socket; print(socket.gethostbyname('mlflow'))"
```

### Scale API thủ công

```bash
kubectl scale deployment iris-api -n iris-mlops --replicas=3
kubectl get pods -n iris-mlops -w
```

### Cập nhật image và rollback

```bash
kubectl set image deployment/iris-api \
  -n iris-mlops api=iris-api:1.1

kubectl rollout status deployment/iris-api -n iris-mlops
kubectl rollout history deployment/iris-api -n iris-mlops
kubectl rollout undo deployment/iris-api -n iris-mlops
```

### Thử self-healing

```bash
kubectl get pods -n iris-mlops
kubectl delete pod -n iris-mlops <iris-api-pod-name>
kubectl get pods -n iris-mlops -w
```

Deployment sẽ tạo Pod thay thế để đưa actual state về desired state.

## 11. Cách đọc lỗi Kubernetes

| Trạng thái | Ý nghĩa thường gặp | Nơi kiểm tra |
|---|---|---|
| `Pending` | Thiếu tài nguyên, PVC chưa bind, scheduling lỗi | `kubectl describe pod` |
| `ImagePullBackOff` | Cluster không tìm thấy image hoặc thiếu registry credential | Events, tên/tag image |
| `CrashLoopBackOff` | App khởi động rồi thoát liên tục | `kubectl logs --previous` |
| `Running` nhưng `0/1 Ready` | Readiness/startup probe thất bại | `describe pod`, endpoint health |
| `403` từ MLflow | Host header không nằm trong allowlist | MLflow logs và `--allowed-hosts` |
| `No such artifact` | Experiment dùng local artifact URI mà API Pod không truy cập được | Artifact URI và cấu hình proxy |
| Service không kết nối | Selector sai, Pod chưa ready hoặc targetPort sai | `kubectl get endpoints` |

Quy trình debug nên theo thứ tự:

```text
Pod tồn tại?
  → Container chạy?
    → Log nói gì?
      → Probe có pass?
        → Service có endpoint?
          → DNS/network hoạt động?
            → Storage/config đúng?
```

## 12. Model lifecycle trong Kubernetes

Một flow MLOps rõ ràng hơn:

```text
1. Training Job
       │
       ▼
2. Log metrics + model vào MLflow
       │
       ▼
3. Đánh giá accuracy / validation rules
       │
       ▼
4. Gán alias champion
       │
       ▼
5. Rollout/restart API để tải model mới
       │
       ▼
6. Theo dõi latency, error rate, drift
```

Code hiện tại chỉ tải model khi process khởi động. Nếu alias `champion` đổi, Pod đang chạy không tự tải model mới. Có ba chiến lược:

1. **Restart Deployment sau promotion**: đơn giản, dễ kiểm soát và phù hợp để học.
2. **API reload model định kỳ**: linh hoạt nhưng phải xử lý concurrency và model consistency.
3. **Build image chứa model**: deployment bất biến và rollback dễ, nhưng mỗi model version cần build image mới.

Với project này, nên bắt đầu bằng chiến lược 1:

```bash
kubectl rollout restart deployment/iris-api -n iris-mlops
kubectl rollout status deployment/iris-api -n iris-mlops
```

## 13. Từ môi trường học tập đến production

Kiến trúc SQLite + PVC + một MLflow replica phù hợp để học, không phải thiết kế production hoàn chỉnh.

### Nên thay đổi ở production

| Thành phần học tập | Hướng production |
|---|---|
| SQLite trên PVC | PostgreSQL/MySQL managed hoặc HA |
| Artifact trên PVC | S3, GCS, Azure Blob hoặc MinIO |
| MLflow `replicas: 1` | Nhiều replica nếu backend/job system hỗ trợ |
| `port-forward` | Ingress/Gateway + TLS + DNS |
| Local image | Container registry |
| ConfigMap chứa mọi cấu hình | Secret/external secret manager cho credential |
| Manual alias | Pipeline có evaluation và approval |
| Log qua `kubectl logs` | Centralized logging |
| CPU-only HPA | Metrics phù hợp workload inference |
| Không authentication | Authentication, authorization và network policy |

Kiến trúc production khái quát:

```text
Client
  │
Ingress / Gateway + TLS
  │
Iris API Deployment (n replicas)
  │
MLflow Tracking Service
  ├── PostgreSQL: metadata + registry
  └── S3/MinIO: model artifacts
```

## 14. Lộ trình học đề xuất

### Giai đoạn 1: nền tảng

1. Pod, Deployment, Service.
2. Labels, selectors và namespaces.
3. ConfigMap, Secret.
4. Logs, describe, events và exec.

### Giai đoạn 2: vận hành project này

1. PVC cho MLflow.
2. Startup/readiness/liveness probes.
3. Training Job.
4. Rolling update và rollback API.
5. Port-forward, sau đó Ingress.

### Giai đoạn 3: MLOps production

1. PostgreSQL và object storage.
2. CI build/test/push image.
3. CD hoặc GitOps với Argo CD/Flux.
4. Prometheus/Grafana và centralized logging.
5. Model evaluation, approval, promotion và rollback.
6. Data/model drift monitoring.

Đừng bắt đầu bằng Helm, service mesh hoặc autoscaling phức tạp trước khi hiểu rõ Pod, Deployment, Service, probe, ConfigMap và PVC. Sáu khái niệm đó giải thích phần lớn hành vi bạn sẽ gặp ở project hiện tại.

## 15. Checklist tự đánh giá

Bạn đã hiểu nền tảng khi có thể tự trả lời:

- Vì sao không nên gọi trực tiếp IP của Pod?
- Deployment khác Pod ở điểm nào?
- Service tìm Pod bằng gì?
- Tại sao database/artifact cần PVC hoặc external storage?
- Readiness khác liveness thế nào?
- Vì sao API Pod không nên mount filesystem local của MLflow node?
- Tại sao training phù hợp với Job hơn Deployment?
- Đổi alias `champion` có tự cập nhật model trong API đang chạy không?
- Vì sao SQLite + một PVC hạn chế khả năng scale MLflow?
- Khi gặp `CrashLoopBackOff`, ba lệnh đầu tiên cần chạy là gì?

## 16. Tài liệu chính thức nên đọc

- [Kubernetes Overview](https://kubernetes.io/docs/concepts/overview/)
- [Kubernetes Concepts](https://kubernetes.io/docs/concepts/)
- [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/)
- [Kubernetes Configuration](https://kubernetes.io/docs/concepts/configuration/)
- [Kubernetes Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/)
- [MLflow Tracking Server](https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/)
- [MLflow Artifact Store](https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/)

---

### Ý chính cần nhớ

```text
Docker đóng gói và chạy container.
Kubernetes giữ cho cả hệ thống container đạt trạng thái mong muốn.

Deployment quản lý Pod.
Service tạo địa chỉ mạng ổn định.
ConfigMap/Secret cung cấp cấu hình.
PVC giữ dữ liệu bền vững.
Probe quyết định Pod sống và sẵn sàng.
Job chạy training hữu hạn.

Trong project Iris:
API nên tải model qua MLflow Service,
MLflow quản lý metadata và proxy artifact,
storage phải tồn tại ngoài vòng đời Pod.
```
