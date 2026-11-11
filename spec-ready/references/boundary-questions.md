# Boundary questions

Ask these when the plan creates or moves a component boundary and the `software-design-rules`
skill is not installed. Record the answers in the spec under "Boundaries and rules applied".

1. **What depends on what?** Which component calls which, and does every dependency point toward
   the part that holds the rules (and away from frameworks, devices and vendors)?
2. **Where does I/O live?** Which component talks to the network, disk, devices or other services,
   and can the core be built and tested without them?
3. **What must stay replaceable?** Which detail (a vendor, a model, a storage engine, a driver) is
   likely to change, and what interface keeps that change out of the core?
