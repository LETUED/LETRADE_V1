graph TB
    %% External Layer
    subgraph "External Services"
        User[User<br/>Web/Mobile/CLI]
        Exchanges[Cryptocurrency Exchanges<br/>Binance/OKX/Gate.io]
        TelegramAPI[Telegram API]
        BlockchainNodes[Blockchain Nodes<br/>ETH/Cosmos/Solana]
    end
    
    %% Load Balancer Layer
    subgraph "Load Balancing Layer"
        GlobalLB[Global Load Balancer<br/>Multi-Region]
        RegionalLB1[Regional LB<br/>US-Central]
        RegionalLB2[Regional LB<br/>Asia-Northeast]
        RegionalLB3[Regional LB<br/>Europe-West]
    end
    
    %% Kubernetes Clusters
    subgraph "Primary Region: US-Central"
        subgraph "Kubernetes Cluster 1"
            subgraph "Control Plane"
                APIServer1[API Server]
                Scheduler1[Scheduler]
                Controller1[Controller Manager]
                etcd1[(etcd)]
            end
            
            subgraph "Application Nodes"
                subgraph "Core Services Pod"
                    CoreEngine1[Core Engine<br/>2 replicas]
                    CapitalMgr1[Capital Manager<br/>1 replica]
                    MLPipeline1[ML Pipeline<br/>3 replicas]
                end
                
                subgraph "Trading Services Pod"
                    TAWorkers1[TA Strategy Workers<br/>5 replicas]
                    RLWorkers1[RL Strategy Workers<br/>3 replicas]
                    GridWorkers1[Grid Workers<br/>5 replicas]
                    DCAWorkers1[DCA Workers<br/>3 replicas]
                end
                
                subgraph "Exchange Services Pod"
                    BinanceConn1[Binance Connector<br/>2 replicas]
                    OKXConn1[OKX Connector<br/>2 replicas]
                    StakingMgr1[Staking Manager<br/>2 replicas]
                end
                
                subgraph "Intelligence Services Pod"
                    BacktestEngine1[Backtest Engine<br/>2 replicas]
                    PerfAnalyzer1[Performance Analyzer<br/>2 replicas]
                    RiskMonitor1[Risk Monitor<br/>3 replicas]
                end
            end
            
            subgraph "GPU Nodes"
                MLTraining1[ML Training Jobs<br/>GPU Enabled]
                Inference1[Model Inference<br/>GPU Accelerated]
            end
            
            subgraph "Data Layer"
                PostgresPrimary1[(PostgreSQL<br/>Primary)]
                PostgresReplica1[(PostgreSQL<br/>Read Replicas)]
                Redis1[(Redis Cluster<br/>Cache)]
                TimescaleDB1[(TimescaleDB<br/>Time-series)]
            end
            
            subgraph "Message Layer"
                RabbitMQ1[RabbitMQ Cluster<br/>3 nodes]
                Kafka1[Kafka Cluster<br/>Market Data Stream]
            end
        end
    end
    
    %% Secondary Regions (Simplified)
    subgraph "Secondary Region: Asia-Northeast"
        subgraph "Kubernetes Cluster 2"
            CoreServices2[Core Services<br/>Standby]
            TradingServices2[Trading Services<br/>Active]
            DataLayer2[(Data Layer<br/>Replicated)]
            MessageLayer2[Message Layer]
        end
    end
    
    subgraph "Secondary Region: Europe-West"
        subgraph "Kubernetes Cluster 3"
            CoreServices3[Core Services<br/>Standby]
            TradingServices3[Trading Services<br/>Active]
            DataLayer3[(Data Layer<br/>Replicated)]
            MessageLayer3[Message Layer]
        end
    end
    
    %% Monitoring & Security Layer
    subgraph "Monitoring & Security"
        subgraph "Observability Stack"
            Prometheus[Prometheus<br/>Metrics]
            Grafana[Grafana<br/>Dashboards]
            ELK[ELK Stack<br/>Logs]
            Jaeger[Jaeger<br/>Tracing]
        end
        
        subgraph "Security Stack"
            Istio[Istio Service Mesh<br/>mTLS, Traffic Mgmt]
            OPA[Open Policy Agent<br/>Policy Enforcement]
            Falco[Falco<br/>Runtime Security]
            Vault[HashiCorp Vault<br/>Secrets]
        end
    end
    
    %% ML Platform
    subgraph "ML Platform"
        Kubeflow[Kubeflow<br/>ML Workflows]
        MLflow[MLflow<br/>Experiment Tracking]
        ModelRegistry[Model Registry<br/>Version Control]
        FeatureStore[Feature Store<br/>Feature Management]
    end
    
    %% Storage Layer
    subgraph "Persistent Storage"
        GCS[Google Cloud Storage<br/>Model Artifacts]
        PersistentVolumes[Persistent Volumes<br/>Application Data]
        BackupStorage[Backup Storage<br/>Multi-Region]
    end
    
    %% CI/CD Pipeline
    subgraph "CI/CD & GitOps"
        GitHub[GitHub<br/>Source Code]
        CloudBuild[Cloud Build<br/>Build Pipeline]
        ArgoCD[ArgoCD<br/>GitOps Deployment]
        ContainerRegistry[Container Registry<br/>Image Storage]
    end
    
    %% Connections
    User -->|HTTPS| GlobalLB
    GlobalLB --> RegionalLB1
    GlobalLB --> RegionalLB2
    GlobalLB --> RegionalLB3
    
    RegionalLB1 --> APIServer1
    
    %% Core Service Connections
    CoreEngine1 --> RabbitMQ1
    CoreEngine1 --> PostgresPrimary1
    CapitalMgr1 --> Redis1
    
    %% Trading Service Connections
    TAWorkers1 --> Kafka1
    RLWorkers1 --> MLPipeline1
    GridWorkers1 --> PostgresPrimary1
    
    %% Exchange Connections
    BinanceConn1 -->|WebSocket/REST| Exchanges
    OKXConn1 -->|WebSocket/REST| Exchanges
    StakingMgr1 -->|Web3| BlockchainNodes
    
    %% ML Platform Connections
    MLPipeline1 --> Kubeflow
    MLTraining1 --> MLflow
    MLTraining1 --> GCS
    
    %% Monitoring Connections
    APIServer1 --> Prometheus
    Prometheus --> Grafana
    All --> ELK
    
    %% Security
    Istio -.->|Service Mesh| All
    Vault -->|Secrets| All
    
    %% CI/CD Flow
    GitHub --> CloudBuild
    CloudBuild --> ContainerRegistry
    ContainerRegistry --> ArgoCD
    ArgoCD --> APIServer1
    
    %% Data Replication
    PostgresPrimary1 -.->|Replication| DataLayer2
    PostgresPrimary1 -.->|Replication| DataLayer3
    
    %% Telegram Integration
    TelegramInterface -->|Bot API| TelegramAPI
    
    %% Styling
    classDef external fill:#ffcccc,stroke:#ff6666
    classDef k8s fill:#ccccff,stroke:#6666ff
    classDef data fill:#ccffcc,stroke:#66ff66
    classDef ml fill:#ffffcc,stroke:#ffff66
    classDef security fill:#ffccff,stroke:#ff66ff
    
    class User,Exchanges,TelegramAPI,BlockchainNodes external
    class APIServer1,Scheduler1,Controller1,CoreEngine1,CapitalMgr1 k8s
    class PostgresPrimary1,PostgresReplica1,Redis1,TimescaleDB1 data
    class MLPipeline1,MLTraining1,Kubeflow,MLflow ml
    class Istio,OPA,Falco,Vault security