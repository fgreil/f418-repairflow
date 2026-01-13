# f418-repairflow
Towards a simple but efficient workflow for mobile phone repair shops.

My example why building new custom new software is nowadays probably more efficient than buying a huge software suite(s) and painfully customizing them (and their interconnections).

## Possible states of a repair
1. Intake & Quoting: Device is still with the client
    * `pending_quote` &mdash; Initial submission, awaiting price confirmation
    * `quoted` &mdash; Price provided to customer
    * `confirmed` &mdash; Customer accepted quote
2. Work Execution: Device is in the shop
   *  `scheduled` &mdash; Work allocated to a technician/time slot. Transition into this state at the moment the device arrived in the shop.
   * `diagnosing` &mdash; Device aDetermining fault and repair scope
   * `awaiting_parts` &mdash; Required materials not yet available  
   * `in_progress` &mdash; Device is currently on work bench
   * `on_hold` &mdash; temporarily paused by customer
   * `ready_for_pickup` &mdash; Customer can collect or ready to ship
4. Post-work status: Device left the shop, but is not yet with the client
   * `in_transit` &mdash; Device handed over to parcel service.
5. Outcomes & Closure: Device is back with the client
   * `collected` &mdash; Device was returned to customer, waiting for feedback by customer.
   * `rejected` &mdash; Quote/repair declined by customer. Transistion to `archived` occurs automatically after 3 months.
   * `cancelled` &mdash; Request cancelled at any stage by the repair shop. Transistion to `archived` occurs automatically after 3 months.
   * `feedback_received` &mdash; Customer filled out the feedback form. Transistion to `archived` occurs automatically after 3 months.
   * `archived` &mdash; Fully closed and retained for records. Final state.

## Howto
For now, there is no MVP (=minimal viable product) yet. What's available already:

1. Take a look at the sample one-page-site [repair-wizard.html](repair-wizard.html). Just download the file and open it in your favorite browser.
2. The file [flow.mmd](flow.mmd) is a **Mermaid diagram**. It is a basically text-based diagramming (top-left switch: `code`) using a simple, human-readable syntax. Github auto-magically plots the flowchart (top-left switch `Preview`).
3. The same flow is also available as [flow.bpmn](flow.bpmn). BPMN stands for **Business Process Model and Notation** &nbsp; the abundant, industry-recognized syntax. You will need viewers like the [Camunda modeler](https://camunda.com/de/download/modeler/) to view the diagram.
4. The folder `data` contains a (AI-generated and not verified) list of smartphone models and their respective repair types.
