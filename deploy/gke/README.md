# Chapter 11 — deploying to the cloud (GKE). Read-only notes: no
# cloud account is needed to read this, and nothing here is run by
# the tests. The book's sequence:
#
# 1. Create a GKE cluster:
#      gcloud container clusters create pylog --num-nodes=3
# 2. Push the image to Google's Container Registry:
#      docker tag pylog:latest gcr.io/<PROJECT>/pylog:latest
#      docker push gcr.io/<PROJECT>/pylog:latest
# 3. Point kubectl at the cluster:
#      gcloud container clusters get-credentials pylog
# 4. Install Metacontroller (the book's custom controllers):
#      kubectl apply -f https://raw.githubusercontent.com/metacontroller/metacontroller/master/manifests/metacontroller.yaml
#    Metacontroller lets you write controllers as plain webhooks; the
#    book adds a service-per-pod load-balancer hook so each Raft
#    member is individually reachable from outside the cluster.
# 5. Deploy the Helm chart with the GCR image, then expose it:
#      helm install pylog deploy/helm/pylog \
#        --set image.repository=gcr.io/<PROJECT>/pylog
#      kubectl expose statefulset pylog --type=LoadBalancer --port=8401
#
# What changes vs local Kind: the image registry, stable DNS names
# (Raft advertises the fully qualified domain name), and the
# load-balancer hook. The service code does not change.
