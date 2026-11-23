# Persistent Storage Dashboard — Kubernetes 

A Flask UI that saves records to `/data/records.json`. Kubernetes mounts a PVC at `/data`; the PVC binds to a local PV on the `microservices-worker` Kind node.

## Requirements
Docker Desktop, Kind, kubectl, and the existing Kind cluster named `microservices`.

## Run in Windows PowerShell

Open PowerShell in this project folder.

### 1. Check cluster and worker name
```powershell
kubectl config current-context
kubectl get nodes
```
Expected context: `kind-microservices`. The worker must be named `microservices-worker`.

### 2. Create storage directory inside the Kind worker
```powershell
docker exec microservices-worker mkdir -p /mnt/data/pv-data
```

### 3. Build and load the image
```powershell
docker build -t persistent-dashboard:v1 .
kind load docker-image persistent-dashboard:v1 --name microservices
```

### 4. Create PV and PVC
```powershell
kubectl apply -f k8s/storage.yaml
kubectl get pv
kubectl get pvc
```
Wait for both PV and PVC to show `Bound`.

### 5. Deploy the application
```powershell
kubectl apply -f k8s/app.yaml
kubectl get pods -o wide
kubectl get svc
```
Wait for the Pod to show `Running` and `1/1 Ready`.

### 6. Open the dashboard
Keep this command running in one PowerShell terminal:
```powershell
kubectl port-forward svc/persistent-dashboard 8080:80
```
Open http://localhost:8080 in your browser.

### 7. Demonstrate persistence
1. Add a record in the dashboard.
2. Confirm it appears in Stored records.
3. In a second PowerShell terminal, run:
```powershell
kubectl get pods
kubectl delete pod -l app=persistent-dashboard
kubectl get pods -w
```
4. Wait for the replacement Pod to become Running.
5. Refresh http://localhost:8080. The saved record should still appear.
6. Verify:
```powershell
kubectl get pv,pvc,pods
kubectl describe pvc persistent-dashboard-pvc
```

## Useful checks
```powershell
kubectl describe pv persistent-dashboard-pv
kubectl describe pod -l app=persistent-dashboard
kubectl logs deployment/persistent-dashboard
```

## Cleanup
```powershell
kubectl delete -f k8s/app.yaml
kubectl delete -f k8s/storage.yaml
```
The PV reclaim policy is `Retain`; deleting the PVC does not automatically erase the data directory. To intentionally reset demo data:
```powershell
docker exec microservices-worker rm -f /mnt/data/pv-data/records.json
```
