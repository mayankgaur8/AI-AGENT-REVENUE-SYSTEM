# Upwork Profile — Senior Java & Spring Boot Developer

---

## PROFILE TITLE

```
Senior Java / Spring Boot Developer | Microservices | REST APIs | AWS & Azure | Bug Fixing
```

*Why this works: hits all primary Upwork search terms in order of search volume. "Bug Fixing" at the end captures the highest-intent, highest-urgency searches.*

---

## HOURLY RATE

**Recommended: $85–$110/hr**

- Start at $85 to build initial reviews (first 3–5 jobs)
- Move to $95 after 5 reviews with 5.0 rating
- Target $110 at 10+ reviews — this is the sweet spot for long-term contracts in your stack
- For fixed-price projects: minimum $300, typical range $500–$2000

---

## PROFILE OVERVIEW (2,200 characters — optimized for Upwork algorithm)

```
Your backend is broken and you need it fixed by someone who's done this before.

I'm a Java and Spring Boot developer with 17 years of production experience. I've
debugged critical failures at 2am, rebuilt APIs handling millions of requests, and
migrated legacy Java 8 systems to modern Spring Boot 3 without breaking production.
Here's what that experience actually means for you:

— I identify the root cause of backend issues in under an hour, not days
— I write code that your team can read, maintain, and extend
— I work independently and communicate clearly — you won't need to manage me

WHAT I DO:

API Development & Design
I build REST APIs contract-first using OpenAPI 3.0. Clean structure, proper error
handling, authentication built in from the start — not bolted on later. APIs that
your frontend team can actually work with.

Bug Fixing & Production Debugging
This is where I've spent most of my 17 years. Stack traces, distributed logs,
Hibernate N+1 queries, Spring Security misconfigurations, JVM memory leaks — I've
seen them all. Most issues are resolved within 4–8 hours.

Microservices Architecture
I've designed event-driven systems using Kafka, built service meshes, implemented
circuit breakers with Resilience4j, and set up distributed tracing with Zipkin.
I know where microservices break because I've built systems that broke the same way.

Performance Optimization
Slow APIs are never a mystery. I run systematic audits — slow query analysis, N+1
detection, cache layer assessment, async processing — and deliver measurable results.
Recent: reduced API P99 latency from 4.2s to 380ms.

Migration Projects
Java 8 → 17. Spring Boot 2.x → 3.x. I've completed 9 of these migrations. I use
OpenRewrite for automated refactoring, then manual review of security config and
behavioral regression testing. Clean, reviewable commits — not a massive diff.

Cloud Deployment
AWS (ECS, EKS, Lambda, RDS) and Azure (AKS, App Service, Functions). I've deployed
and debugged production environments on both platforms.

TECH STACK: Java 8/11/17/21 · Spring Boot · Spring Security · Microservices ·
Kafka · REST APIs · React · Angular · AWS · Azure · PostgreSQL · MySQL · MongoDB ·
Docker · Kubernetes · Redis · JUnit · Mockito

If you have a backend problem, I can solve it. Message me with your issue — I'll
tell you within 30 minutes whether I've seen it before and how I'd approach it.
```

---

## TOP 15 SKILLS (in priority order)

```
1. Java
2. Spring Boot
3. REST API Development
4. Microservices Architecture
5. API Debugging & Bug Fixing
6. AWS (Amazon Web Services)
7. Microsoft Azure
8. Apache Kafka
9. React
10. PostgreSQL / SQL
11. Docker & Kubernetes
12. Spring Security / OAuth2
13. Performance Optimization
14. MongoDB
15. CI/CD (GitHub Actions, Jenkins)
```

---

## 3 PORTFOLIO PROJECT DESCRIPTIONS

### Portfolio Project 1 — Payment API Debugging & Optimization

**Title:** Resolved Critical Payment Processing Bug — €0 in Lost Revenue After Fix

```
A fintech client was experiencing intermittent payment failures affecting 3–5% of
transactions. No error in the logs, no pattern in the data — just silent failures
that customers only noticed when checking their account.

Root cause: a race condition in the transaction commit sequence combined with a
connection pool timeout that only surfaced under load above 200 concurrent users.
The ORM was releasing the connection before the async notification event fired.

Fix: redesigned the transaction boundary, moved the notification to a Kafka event
(decoupling it from the HTTP request lifecycle), and added idempotency keys to
prevent duplicate processing on retry.

Result: zero payment failures in the 3 months post-fix. Transaction throughput
increased 40% as a side effect of the connection pool fix.

Stack: Java 17 · Spring Boot 3 · PostgreSQL · Kafka · AWS RDS
```

---

### Portfolio Project 2 — Microservices Performance Overhaul

**Title:** Reduced API Latency 82% — From 4.2s to 380ms P99

```
An e-commerce client's checkout API was degrading during peak hours. The SLA was
500ms P99 — they were hitting 4+ seconds. Engineers had spent 3 weeks adding
caching and horizontal scaling without improvement.

The actual problem: 47 N+1 queries hidden inside a single checkout request,
combined with a synchronous inventory check to a slow third-party service on every
add-to-cart call.

Solution: rewrote the product query using JOIN FETCH with batch size configuration
(eliminated 43 of the 47 N+1 queries), moved the inventory check to an async
Kafka event with a local cache as the source of truth, and added Redis caching for
product catalog data with a 5-minute TTL.

Result: P99 latency dropped from 4.2s to 380ms. Infrastructure cost reduced by
30% because they no longer needed the extra instances they'd added trying to scale
out of the problem.

Stack: Java 11 · Spring Boot 2.7 · Kafka · Redis · PostgreSQL · AWS ECS
```

---

### Portfolio Project 3 — Spring Boot 3 Migration (Legacy System)

**Title:** Migrated 200K-Line Java 8 Codebase to Spring Boot 3 / Java 17 — Zero Downtime

```
A logistics company needed to migrate their core operations platform from Java 8 /
Spring Boot 2.3 to Java 17 / Spring Boot 3. The system processed 50,000+ shipments
per day. Zero downtime was a hard requirement.

Challenges: 200,000+ lines of code, 8 years of accumulated technical debt, heavy
use of deprecated Spring Security APIs, custom Hibernate dialect that needed a
full rewrite for Hibernate 6, and two third-party libraries that weren't Jakarta
EE compatible.

Approach: OpenRewrite for automated javax → jakarta migration (handled ~60% of
changes), feature branch with side-by-side API comparison testing, phased rollout
using blue-green deployment on AWS.

Result: full migration completed in 11 days with zero production incidents. Test
coverage increased from 34% to 61% as a side effect of the work (added tests to
cover behavioral changes during migration review).

Stack: Java 8 → 17 · Spring Boot 2.3 → 3.1 · AWS · PostgreSQL · Docker · Jenkins
```

---
