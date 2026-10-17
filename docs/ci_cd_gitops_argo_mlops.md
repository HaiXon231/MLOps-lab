# CI/CD, GitOps và Argo trong MLOps

Tài liệu này giải thích ngắn gọn nhưng có hệ thống về **CI/CD trong MLOps**, **GitOps**, và bộ công cụ **Argo**, dựa trên đúng flow đang được dùng trong project thực hành.

---

# 1. CI/CD trong MLOps thực chất là gì?

Trước hết, hãy nhìn một application bình thường.

Bạn sửa code:

```text
Developer
   ↓
git push
   ↓
???
   ↓
Version mới chạy trên server
```

Phần `???` chính là nơi **CI/CD** xuất hiện.

## 1.1. CI — Continuous Integration

CI trả lời câu hỏi:

> **Code mới có đủ an toàn để tạo thành một phiên bản mới hay không?**

Ví dụ bạn push FastAPI lên GitHub:

```text
git push
   ↓
GitHub Actions
   ↓
Install dependencies
   ↓
Run tests
   ↓
Build Docker image
```

Nếu test fail:

```text
Code
 ↓
CI
 ↓
❌ Failed

Không tạo release/deploy
```

Nếu pass:

```text
Code
 ↓
CI
 ↓
✓ Tests
 ↓
Docker Image
```

Vì vậy khi tạo:

```text
tests/test_training.py
```

và:

```text
.github/workflows/pipeline.yml
```

mục đích không chỉ là học `pytest`.

Ta đang xây một **quality gate**:

```text
Code mới
   ↓
Có hoạt động đúng không?
   ↓
Yes → đi tiếp
No  → dừng
```

---

# 2. Tại sao CI lại build Docker image?

Sau khi test xong, ta cần tạo **artifact để deploy**.

Trong web app truyền thống, artifact có thể là:

```text
.jar
binary
bundle
```

Trong hệ thống Kubernetes của project, artifact deploy là:

```text
Docker Image
```

Vì vậy:

```text
Source Code
   ↓
CI
   ↓
Docker Image
```

Ví dụ:

```text
Git commit:

a82f91c
```

tạo:

```text
iris-api:a82f91c
```

Điều này giúp trace được:

```text
Pod đang chạy image a82f91c
        ↓
image này được build từ
        ↓
Git commit a82f91c
```

Đây là **traceability**.

---

# 3. Container Registry nằm ở đâu?

Docker image được tạo xong phải có một nơi lưu.

Ví dụ:

```text
GitHub Container Registry
Amazon ECR
Docker Hub
```

Luồng trở thành:

```text
Code
 ↓
CI
 ↓
Docker Build
 ↓
Container Registry
```

Trong bài local:

```text
GitHub Actions
      ↓
     GHCR
```

Project thật trên AWS:

```text
GitHub Actions
      ↓
     ECR
```

Có thể phân biệt:

```text
Git
→ lưu source code

Container Registry
→ lưu Docker images

MLflow Model Registry
→ lưu/quản lý các model versions
```

Ba loại registry/repository này giải quyết ba vấn đề khác nhau.

---

# 4. CD — Continuous Delivery / Deployment

Sau khi image mới đã có:

```text
iris-api:v2
```

câu hỏi tiếp theo là:

> Làm sao Kubernetes biết phải chuyển từ v1 sang v2?

Cách thủ công:

```bash
kubectl set image ...
```

Tức:

```text
Developer
   ↓
kubectl
   ↓
Kubernetes
```

Nhưng production không muốn phụ thuộc vào việc một người nhớ chạy command.

CD tự động hóa đoạn này:

```text
New Image
   ↓
Deployment config thay đổi
   ↓
Kubernetes
   ↓
Rolling Update
```

---

# 5. Cách CD truyền thống

Một CI/CD pipeline có thể làm:

```text
GitHub Actions
      ↓
docker build
      ↓
docker push
      ↓
kubectl apply
```

Tức GitHub Actions **push thay đổi trực tiếp vào cluster**.

Kiểu này có thể chạy được, nhưng trạng thái cluster phụ thuộc khá nhiều vào những command pipeline đã thực thi.

---

# 6. GitOps là gì?

GitOps thay đổi tư duy.

Thay vì nói:

> “Pipeline hãy chạy command để cluster trở thành version 2.”

Ta ghi vào Git:

```yaml
image: iris-api:v2
```

và xem Git là nơi mô tả trạng thái mà cluster phải đạt tới.

Ví dụ:

```text
Git Repository

deployment.yaml

image: iris-api:v2
replicas: 3
```

đây là:

```text
Desired State
```

Cluster hiện tại:

```text
image: iris-api:v1
replicas: 3
```

đây là:

```text
Actual State
```

GitOps controller phát hiện:

```text
Desired != Actual
```

và reconcile:

```text
Kubernetes
v1
 ↓
v2
```

Mental model ngắn nhất:

> **GitOps = lưu trạng thái mong muốn của hệ thống trong Git và để một controller tự đồng bộ hệ thống thực tế về trạng thái đó.**

```text
                  GIT
                   │
             Desired State
                   │
                   ↓
              GitOps Controller
                   │
             compare / sync
                   │
                   ↓
              Kubernetes
               Actual State
```

Git trở thành **source of truth**.

---

# 7. Tại sao GitHub Actions không deploy thẳng nữa?

Trong kiến trúc hiện tại:

```text
GitHub Actions
      ↓
build image
      ↓
push GHCR
      ↓
update Git manifest
```

Sau đó GitHub Actions **dừng**.

Nó không cần:

```text
kubectl apply
```

Argo CD sẽ xử lý phần còn lại:

```text
Git
 ↓
Argo CD
 ↓
Kubernetes
```

Đây chính là **CD theo GitOps**.

---

# 8. Toàn bộ CI/CD + GitOps của project hiện tại

```text
Developer
   ↓
git push
   ↓
GitHub Actions
   │
   ├── pytest
   │
   ├── build Docker
   │
   └── push GHCR
   │
   ↓
update kustomization.yaml

newTag: a82f91c

   ↓
git commit
   ↓
Git Repository
   ↓
Argo CD
   ↓
phát hiện Git khác Cluster
   ↓
Kubernetes Deployment
   ↓
Rolling Update
   ↓
new Pods
```

Vai trò từng thành phần:

| Thành phần | Vai trò |
|---|---|
| GitHub | lưu source + manifests |
| GitHub Actions | CI automation |
| pytest | kiểm tra code |
| Docker | đóng gói application |
| GHCR / ECR | lưu image |
| Kubernetes manifests | mô tả desired state |
| Argo CD | GitOps CD |
| Kubernetes | chạy application |

---

# 9. CI/CD trong MLOps khác DevOps ở đâu?

Pipeline hiện tại chủ yếu là:

```text
Code
 ↓
Test
 ↓
Build
 ↓
Deploy
```

Đây vẫn chủ yếu là **application CI/CD**.

Nhưng MLOps còn có:

```text
Data
 ↓
Train
 ↓
Evaluate
 ↓
Model Registry
 ↓
Deploy Model
```

Và một trigger khác có thể là:

```text
New Data
```

thay vì:

```text
New Code
```

Vì vậy MLOps thường có thêm:

```text
CT
= Continuous Training
```

Mental model:

```text
CI
→ code có ổn không?

CD
→ đưa version mới ra môi trường chạy

CT
→ có cần train model mới không?
```

Project hiện tại đang học **CI/CD trước**.

Sau này mới nối:

```text
New Data
 ↓
Training Job
 ↓
Evaluation
 ↓
MLflow
 ↓
Candidate
 ↓
Deployment
```

---

# 10. Argo là gì?

**Argo là một ecosystem các công cụ dành cho Kubernetes.**

Các công cụ liên quan trực tiếp tới project:

| Tool | Vai trò |
|---|---|
| **Argo CD** | GitOps Continuous Delivery |
| **Argo Rollouts** | Canary / Blue-Green / progressive delivery |
| **Argo Workflows** | workflow/job dạng DAG trên Kubernetes |

Trong project hiện tại, quan trọng nhất trước mắt là:

```text
Argo CD
```

Sau này, khi làm Canary mới dùng:

```text
Argo Rollouts
```

---

# 11. Argo CD là gì?

Argo CD là:

> **GitOps Continuous Delivery controller cho Kubernetes.**

Nó chạy bên trong hoặc kết nối với Kubernetes cluster.

Ví dụ:

```text
Kubernetes Cluster
│
├── Argo CD
│
├── FastAPI Pods
│
├── MLflow
│
└── Services
```

Argo CD liên tục nhìn:

```text
Git Repository
```

và:

```text
Kubernetes Cluster
```

rồi so sánh.

---

# 12. Ví dụ Argo CD hoạt động

Git:

```yaml
replicas: 3

image:
  iris-api:v2
```

Cluster hiện tại:

```text
replicas = 3
image = iris-api:v1
```

Argo CD thấy:

```text
OutOfSync
```

sau đó apply desired state:

```text
v1 Pods
 ↓
rolling update
 ↓
v2 Pods
```

Khi xong:

```text
Synced
Healthy
```

---

# 13. `Synced` và `Healthy` khác nhau

`Synced` nghĩa là:

> Kubernetes configuration hiện tại giống Git.

`Healthy` nghĩa là:

> Resource đang hoạt động ở trạng thái được coi là khỏe.

Ví dụ:

```text
Git và Cluster giống nhau

→ Synced ✓

Nhưng Pod CrashLoopBackOff

→ Healthy ✗
```

Hai khái niệm này khác nhau.

---

# 14. Tại sao cần Argo CD khi Kubernetes đã có control loop?

Kubernetes control loop chỉ biết:

```text
Kubernetes objects hiện tại
```

Nó không tự biết:

> Git repository muốn gì?

Ví dụ Kubernetes thấy:

```text
Deployment
replicas = 3
```

thì nó giữ 3 replicas.

Nhưng nếu Git đổi:

```text
replicas = 5
```

Kubernetes không tự đọc Git.

Argo CD tạo cầu nối:

```text
Git
 ↓
Argo CD
 ↓
Kubernetes API
```

Tức:

```text
Git desired state
      ↓
Argo CD
      ↓
Kubernetes desired state
      ↓
Kubernetes controllers
      ↓
Pods
```

Có thể coi là **hai tầng reconciliation**.

---

# 15. Argo CD khác GitHub Actions thế nào?

Đây là chỗ rất dễ nhầm.

```text
GitHub Actions
→ làm công việc khi event xảy ra

Argo CD
→ liên tục đảm bảo cluster giống Git
```

GitHub Actions mang tính:

```text
event-driven pipeline

git push
↓
run job
↓
xong
```

Argo CD mang tính:

```text
controller

watch
↓
compare
↓
reconcile
↓
watch
↓
compare
...
```

Argo CD không thay thế CI.

---

# 16. Nếu ai đó tự sửa cluster thì sao?

Giả sử Git nói:

```text
replicas = 3
```

nhưng bạn chạy:

```bash
kubectl scale deployment iris-api --replicas=10
```

Cluster thành:

```text
replicas = 10
```

Argo CD thấy:

```text
Git     = 3
Cluster = 10
```

Nếu bật:

```yaml
selfHeal: true
```

Argo CD sẽ đưa về:

```text
3
```

Đây là lý do gọi:

```text
Git = source of truth
```

---

# 17. Argo Rollouts là gì?

Kubernetes `Deployment` mặc định chủ yếu hỗ trợ Rolling Update.

Ví dụ:

```text
v1 v1 v1
↓
v2 v1 v1
↓
v2 v2 v1
↓
v2 v2 v2
```

Nhưng không có sẵn logic mạnh kiểu:

```text
10% traffic
↓
check Prometheus
↓
good?
↓
50%
↓
check again
↓
100%
```

Argo Rollouts bổ sung **progressive delivery** như:

- Canary
- Blue-Green
- promotion
- rollback theo metric

---

# 18. Argo CD và Argo Rollouts phối hợp thế nào?

```text
GitHub
 ↓
GitHub Actions
 ↓
Git Manifest
 ↓
Argo CD
 ↓
Argo Rollout
 ↓
Candidate Pods
        +
Stable Pods
 ↓
Prometheus metrics
 ↓
Promote / Rollback
```

Vai trò:

```text
Argo CD
→ đưa configuration trong Git vào cluster

Argo Rollouts
→ quyết định rollout version mới như thế nào
```

Không nên nhầm hai cái.

---

# 19. Ví dụ project sau này

Train:

```text
Model v6
```

đã vượt validation.

Build:

```text
iris-api:model-v6
```

CI cập nhật Git:

```yaml
image:
  iris-api:model-v6
```

Argo CD phát hiện:

```text
Git != Cluster
```

và sync.

Nhưng thay vì deploy ngay 100%:

```text
100% → v6
```

Argo Rollouts điều khiển:

```text
10% → v6
90% → v5
```

Prometheus báo tốt:

```text
10%
↓
50%
↓
100%
```

Nếu xấu:

```text
rollback
↓
100% v5
```

Đó chính là phần **Canary + rollback** trong project.

---

# 20. Argo Workflows là gì?

Argo Workflows là một workflow engine cho Kubernetes.

Nó phù hợp với pipeline nhiều bước:

```text
Download Data
      ↓
Preprocess
      ↓
Train
      ↓
Evaluate
      ↓
Register
```

Có thể biểu diễn dưới dạng DAG.

Tuy nhiên project hiện tại **chưa cần Argo Workflows**.

Kubernetes Job + GitHub Actions là đủ cho giai đoạn hiện tại.

Không cần cài tất cả công cụ Argo chỉ vì chúng cùng tên.

---

# 21. Mental model cuối cùng

## Source / CI

```text
Developer
   ↓
GitHub
   ↓
GitHub Actions
   ↓
Test
   ↓
Docker Build
   ↓
Container Registry
```

## GitOps / CD

```text
Git Manifest
    ↓
Argo CD
    ↓
Kubernetes
```

## Safe Deployment

```text
Kubernetes
    ↓
Argo Rollouts
    ↓
Canary
    ↓
Prometheus
    ↓
Promote / Rollback
```

## Machine Learning

```text
Data
 ↓
Training
 ↓
Evaluation
 ↓
MLflow Registry
 ↓
Candidate Model
 ↓
CI/CD path phía trên
```

---

# 22. Liên hệ trực tiếp với các bước thực hành

Khi tạo:

```text
pytest
```

→ xây **CI quality gate**.

Khi chạy:

```text
docker build
```

→ tạo **deployable artifact**.

Khi push image lên:

```text
GHCR
```

→ tạo **central artifact repository**.

Khi chỉnh:

```text
kustomization.yaml
```

→ cập nhật **desired deployment state**.

Khi cài:

```text
Argo CD
```

→ tạo **GitOps controller**.

Khi Argo CD tự update Kubernetes:

```text
Git
→ Cluster
```

→ đó là **CD theo GitOps**.

Sau này khi thêm:

```text
Argo Rollouts
```

→ ta không thay CI/CD, mà **nâng cấp cách CD rollout version mới an toàn hơn**.

---

# 23. Tóm tắt ngắn

```text
CI
→ kiểm tra và build code mới

CD
→ đưa version mới ra môi trường chạy

GitOps
→ Git lưu desired state, controller tự đồng bộ cluster

Argo CD
→ công cụ GitOps CD cho Kubernetes

Argo Rollouts
→ rollout nâng cao: canary, blue-green, rollback

Argo Workflows
→ orchestration workflow/job trên Kubernetes

CT
→ continuous training khi data/model thay đổi
```

Mental model tổng thể:

```text
Code
 ↓
GitHub Actions
 ↓
Test + Build
 ↓
Container Registry
 ↓
Git Manifest
 ↓
Argo CD
 ↓
Kubernetes
 ↓
Argo Rollouts
 ↓
Canary / Rollback
```

và phía ML:

```text
Data
 ↓
Train
 ↓
Evaluate
 ↓
MLflow Registry
 ↓
Candidate Model
 ↓
Deployment Pipeline
```
