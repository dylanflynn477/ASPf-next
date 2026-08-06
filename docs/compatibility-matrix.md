# Compatibility matrix

“Reference” means implemented through the inspectable `__aspf_value/2`
translation. “Pass-through” means the frontend preserves the construct and
Clingo supplies its ordinary ASP semantics. No row implies full historical
ASP{f} compatibility.

| Construct | 0.1 status | Backend or diagnostic |
| --- | --- | --- |
| `#nherb f/n.` | Supported | Frontend declaration IR |
| Zero-arity `f #= v` | Supported | Reference lowering |
| Ground `f(args) #= value.` | Supported | Reference lowering |
| Conditional assignment head | Supported | Reference lowering |
| Positive body `#=` | Supported | Reference lowering |
| Integer value | Supported | Clingo number symbol |
| Symbolic constant value | Supported | Clingo function symbol, arity 0 |
| String value | Supported | Clingo string symbol |
| Undefined application | Supported | Absence of value atom; no totality |
| Conflicting values | Supported | Functionality constraint; UNSAT |
| Multiple CLI files | Supported | Shared declaration pass |
| Model limit / all models | Supported | Clingo solve configuration |
| Ordinary ASP without n-atoms | Pass-through | Clingo 5.8 |
| Ordinary `#show` | Pass-through | Normalizer preserves assignments |
| `%` and `%* ... *%` comments | Supported | Source scanner |
| Multiline statements | Supported | Source scanner |
| User executable identifier beginning `__aspf_` | Unsupported | Location-aware error |
| Declared symbol outside a supported n-atom | Unsupported | Location-aware error |
| `#!=`, `#<`, `#<=`, `#>`, `#>=` | Unsupported | Location-aware error |
| Default-negated n-atoms | Unsupported | Location-aware error |
| Variables in n-atoms | Unsupported | Location-aware error |
| `_v` non-Herbrand variables | Unsupported | Location-aware error |
| Arithmetic in n-atoms | Unsupported | Location-aware error |
| Aggregates containing n-atoms | Unsupported | Location-aware error |
| Choice/disjunctive constructs containing n-atoms | Unsupported | Location-aware error |
| Declared n-application nested in another | Unsupported | Location-aware error |
| Compound assignment values | Unsupported | Location-aware error |
| Global `#nherb.` | Unsupported | Location-aware error |
| `#show #nherb` / `#hide #nherb` | Unsupported | Location-aware error |
| Native theory-atom backend | Planned only | Not implemented |
| Custom propagator | Planned only | Not implemented |
| Historical grounding-efficiency behavior | Not claimed | Reference backend only |
