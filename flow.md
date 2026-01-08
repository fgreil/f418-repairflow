flowchart LR
    %% Pools / Lanes (logical representation)
    Customer((Customer))
    Staff[Repair Staff]
    System[Shop System]

    %% Start
    Start([Customer reports issue])

    %% Intake
    Intake[Receive phone and record details]
    Estimate[Provide repair estimate]
    Approve{Customer approves estimate?}

    %% Decision paths
    Reject[Return phone unrepaired]
    Diagnose[Diagnose device]

    %% Repair path
    Repair{Repair feasible?}
    Fix[Perform repair]
    Test[Test device]

    %% Outcomes
    Success{Repair successful?}
    Rework[Additional repair required]
    Fail[Declare device unrepairable]

    %% Payment & closure
    Invoice[Generate invoice]
    Payment[Collect payment]
    Return[Return phone to customer]

    %% Flow
    Customer --> Start
    Start --> Intake
    Intake --> Estimate
    Estimate --> Approve

    Approve -- No --> Reject --> Return
    Approve -- Yes --> Diagnose --> Repair

    Repair -- No --> Fail --> Return
    Repair -- Yes --> Fix --> Test --> Success

    Success -- No --> Rework --> Fix
    Success -- Yes --> Invoice --> Payment --> Return
