sequenceDiagram
    %% AI/ML Trading Flow
    participant Market as Market Data
    participant MLPipeline as ML Pipeline
    participant RLAgent as RL Agent
    participant PricePredictor as Price Predictor
    participant RegimeClassifier as Regime Classifier
    participant RLStrategy as RL Strategy
    participant CapitalManager as Capital Manager
    participant RiskManager as Risk Manager
    participant PortfolioOptimizer as Portfolio Optimizer
    participant ExchangeConnector as Exchange
    
    Note over Market,ExchangeConnector: AI/ML Enhanced Trading Flow
    
    %% Data Collection and Feature Engineering
    Market->>MLPipeline: Stream Market Data
    MLPipeline->>MLPipeline: Feature Engineering
    MLPipeline->>MLPipeline: Data Normalization
    
    %% Market Regime Classification
    MLPipeline->>RegimeClassifier: Current Market Features
    RegimeClassifier->>RegimeClassifier: Classify Market Regime
    RegimeClassifier-->>MLPipeline: Bull/Bear/Sideways
    
    %% Price Prediction
    MLPipeline->>PricePredictor: Historical + Current Data
    PricePredictor->>PricePredictor: LSTM Processing
    PricePredictor->>PricePredictor: Ensemble Prediction
    PricePredictor-->>MLPipeline: Price Forecast + Confidence
    
    %% RL Agent Decision Making
    MLPipeline->>RLAgent: State Vector
    Note right of RLAgent: State includes:<br/>- Market features<br/>- Portfolio state<br/>- Risk metrics<br/>- Predictions
    
    RLAgent->>RLAgent: Forward Pass Policy Network
    RLAgent->>RLAgent: Action Selection (ε-greedy)
    RLAgent-->>RLStrategy: Action + Confidence
    
    %% Strategy Execution
    RLStrategy->>RLStrategy: Validate Action
    RLStrategy->>RLStrategy: Calculate Position Size
    
    alt Buy/Sell Signal
        RLStrategy->>CapitalManager: Trade Proposal
        
        %% Risk Assessment
        CapitalManager->>RiskManager: Assess Risk
        RiskManager->>RiskManager: Calculate VaR
        RiskManager->>RiskManager: Check Limits
        RiskManager-->>CapitalManager: Risk Score
        
        %% Portfolio Optimization
        CapitalManager->>PortfolioOptimizer: Current + Proposed Position
        PortfolioOptimizer->>PortfolioOptimizer: Optimize Allocation
        PortfolioOptimizer->>PortfolioOptimizer: Correlation Analysis
        PortfolioOptimizer-->>CapitalManager: Optimal Size
        
        alt Risk Approved
            CapitalManager->>ExchangeConnector: Execute Trade
            ExchangeConnector->>Market: Place Order
            Market-->>ExchangeConnector: Order Filled
            ExchangeConnector-->>CapitalManager: Execution Report
            
            %% Learning from Result
            CapitalManager->>RLAgent: Trade Result
            RLAgent->>RLAgent: Calculate Reward
            RLAgent->>RLAgent: Update Replay Buffer
            
            opt Periodic Training
                RLAgent->>RLAgent: Sample from Buffer
                RLAgent->>RLAgent: Update Networks
                RLAgent->>RLAgent: Save Checkpoint
            end
        else Risk Rejected
            CapitalManager-->>RLStrategy: Trade Denied
            RLStrategy->>RLAgent: Negative Reward
        end
    else Hold Signal
        RLStrategy-->>RLAgent: No Action
    end
    
    %% Continuous Learning Loop
    Note over RLAgent,MLPipeline: Continuous Improvement
    loop Every N Episodes
        RLAgent->>MLPipeline: Performance Metrics
        MLPipeline->>MLPipeline: Analyze Results
        MLPipeline->>RLAgent: Hyperparameter Update
    end