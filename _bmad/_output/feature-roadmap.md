# GarageAI Feature Roadmap & Differentiation Analysis

**Document Type**: Product Feature Analysis
**Author**: Jan (Product Manager)
**Date**: January 2026

---

## Executive Summary

Generic voice AI is commoditized. Our moat is **automotive-specific intelligence** that requires domain knowledge + DMS integration. This document maps current features, identifies gaps, and proposes unique features competitors can't easily replicate.

---

## Part 1: Current Features (What We Have)

### Voice & Telephony
| Feature | Status | Notes |
|---------|--------|-------|
| Twilio phone integration | ✅ Built | Inbound calls work |
| Web browser testing | ✅ Built | Dashboard for demos |
| Dutch language support | ✅ Built | Gemini handles Dutch |
| <800ms latency | ✅ Built | Optimized pipeline |
| 24/7 availability | ✅ Built | Cloud-hosted |

### DMS Integration (WinCar)
| Feature | Status | Tool |
|---------|--------|------|
| Customer lookup by phone | ✅ Built | `identify_customer` |
| Work order status check | ✅ Built | `check_werkorder_status` |
| Parts inventory lookup | ✅ Built | `check_part_stock` |
| Appointment scheduling | ✅ Built | `schedule_appointment` |
| Payment link generation | ✅ Built | `generate_payment_link` |

### AI Capabilities
| Feature | Status | Notes |
|---------|--------|-------|
| Conversational AI | ✅ Built | LangGraph + Gemini |
| Web search fallback | ✅ Built | DuckDuckGo for general questions |
| Emergency detection | ✅ Built | System prompt handles safety |
| Bilingual (NL/EN) | ✅ Built | Auto-detects language |

---

## Part 2: What Generic Voice AI Can Do (Commodity Features)

These features are **NOT differentiators** - every competitor has them:

- Answer phone calls
- Speech-to-text / text-to-speech
- Basic appointment scheduling
- FAQ answering
- Call routing/transfer
- Voicemail transcription
- Business hours handling
- Multi-language support
- CRM logging

**Lesson**: Don't compete on these. They're table stakes.

---

## Part 3: Garage-Specific Features (Our Moat)

These features require **automotive domain knowledge + DMS integration** that generic AI cannot easily replicate.

### Tier 1: High Value, Medium Effort

#### 1. APK Reminder & Scheduling Engine
**What**: Proactively call customers when APK (Dutch MOT) is expiring

**How it works**:
```
System checks DMS nightly →
Finds vehicles with APK expiring in 30 days →
Auto-calls customer: "Uw APK verloopt over 4 weken. Zal ik een afspraak inplannen?"
```

**Why unique**: Requires RDW data understanding + DMS integration + proactive calling
**Value**: Generates revenue for garage, saves customer hassle
**Differentiator score**: ⭐⭐⭐⭐⭐

---

#### 2. Kenteken-to-Vehicle Intelligence
**What**: Customer says license plate, AI instantly knows everything about their car

**How it works**:
```
Customer: "Mijn kenteken is AB-123-CD"
AI: "Ik zie dat u een Volkswagen Golf uit 2019 heeft met 67.000 km.
     Uw laatste onderhoudsbeurt was 8 maanden geleden.
     Volgens de fabrikant is de volgende beurt nu aan de orde."
```

**Why unique**: Requires RDW API + service interval knowledge + DMS history
**Value**: Instant personalization, professional impression
**Differentiator score**: ⭐⭐⭐⭐⭐

---

#### 3. Service Interval Intelligence
**What**: Know when maintenance is due based on manufacturer specs

**How it works**:
```
AI checks:
- Vehicle make/model/year
- Current mileage (from last visit)
- Manufacturer service intervals
- Last service date

Outputs: "Uw BMW 3-serie heeft elke 30.000 km een grote beurt nodig.
         Met uw huidige kilometerstand is dat over ongeveer 5.000 km."
```

**Why unique**: Requires automotive service interval database (by make/model)
**Value**: Positions garage as proactive advisor, not reactive fixer
**Differentiator score**: ⭐⭐⭐⭐⭐

---

#### 4. Intelligent Quote Generation
**What**: Give instant price estimates for common services

**How it works**:
```
Customer: "Wat kost een APK?"
AI: "Een APK bij ons is €34,95. Wilt u direct inplannen?"

Customer: "Wat kost een distributieriem vervangen?"
AI: "Voor uw Volkswagen Golf 1.4 TSI kost een distributieriem
     vervangen ongeveer €450-550 inclusief onderdelen en arbeid.
     Zal ik een offerte laten maken door de werkplaats?"
```

**Why unique**: Requires labor time database + parts pricing + vehicle-specific knowledge
**Value**: Customers get instant answers, no "we'll call you back"
**Differentiator score**: ⭐⭐⭐⭐

---

#### 5. Warranty & Recall Check
**What**: Instantly check if work might be covered under warranty or recall

**How it works**:
```
Customer: "Mijn airbag lampje brandt"
AI: "Ik zie dat uw Volkswagen nog onder fabrieksgarantie valt tot maart 2026.
     Er is ook een actieve terugroepactie voor het airbag-systeem bij dit model.
     Dit kan mogelijk kosteloos worden opgelost. Zal ik een afspraak maken?"
```

**Why unique**: Requires RDW recall database + warranty tracking + OEM knowledge
**Value**: Builds trust, saves customer money, garage gets recall work
**Differentiator score**: ⭐⭐⭐⭐⭐

---

### Tier 2: Medium Value, Lower Effort

#### 6. Smart Symptoms Triage
**What**: Ask intelligent follow-up questions about car problems

**How it works**:
```
Customer: "Mijn auto maakt een raar geluid"
AI: "Om u beter te helpen:
     - Wanneer hoort u het geluid? Bij het remmen, sturen, of rijden?
     - Is het een piepend, knarsend, of tikkend geluid?
     - Links, rechts, voor of achter?"

[After answers]
AI: "Dat klinkt als versleten remblokken aan de voorzijde.
     Wilt u een afspraak maken voor controle?"
```

**Why unique**: Automotive diagnostic knowledge + structured questioning
**Value**: Better prepared work orders, faster diagnosis
**Differentiator score**: ⭐⭐⭐⭐

---

#### 7. Loaner/Replacement Vehicle Availability
**What**: Check and reserve courtesy cars during the call

**How it works**:
```
Customer: "Als ik mijn auto breng, heb ik wel vervoer nodig"
AI: "Ik zie dat we op donderdag een leenauto beschikbaar hebben.
     Zal ik die voor u reserveren bij uw afspraak?"
```

**Why unique**: Requires DMS fleet management integration
**Value**: Removes friction from booking
**Differentiator score**: ⭐⭐⭐

---

#### 8. Parts Availability + ETA
**What**: Not just "in stock" but delivery time if not

**How it works**:
```
Customer: "Hebben jullie een koppakking voor mijn Opel?"
AI: "Die hebben we niet direct op voorraad, maar kan morgen voor 12:00
     geleverd worden. Zal ik hem bestellen en een afspraak maken voor overmorgen?"
```

**Why unique**: Supplier integration + smart ordering
**Value**: Turns "no" into "yes, tomorrow"
**Differentiator score**: ⭐⭐⭐

---

#### 9. Seasonal Service Campaigns
**What**: Contextual upselling based on season

**How it works**:
```
[October call about any topic]
AI: "Trouwens, ik zie dat u nog zomerbanden heeft gemonteerd.
     Wilt u ook de winterbanden laten omwisselen? We kunnen dat combineren."
```

**Why unique**: DMS tire data + seasonal awareness + service history
**Value**: Natural upsell, relevant to customer
**Differentiator score**: ⭐⭐⭐

---

#### 10. Work Order Progress Updates
**What**: Customer calls for status, gets real-time update

**How it works**:
```
Customer: "Is mijn auto al klaar?"
AI: "Ik kijk even... Uw Peugeot is momenteel in de werkplaats.
     De remmen zijn vervangen, de monteur is nu bezig met de APK-keuring.
     Verwachte gereedtijd: 15:30. Ik kan u bellen zodra hij klaar staat."
```

**Why unique**: Real-time work order status + mechanic assignment
**Value**: No more "ik moet het even navragen"
**Differentiator score**: ⭐⭐⭐⭐

---

### Tier 3: Innovative Features (Future)

#### 11. Photo/Video Intake
**What**: Customer sends photo of problem via WhatsApp, AI analyzes

**How it works**:
```
Customer sends photo of dashboard warning light
AI: "Ik zie een motorstoring lampje. Dit kan verschillende oorzaken hebben.
     Ik raad aan om niet ver te rijden. Zal ik een diagnose-afspraak maken?"
```

**Why unique**: Vision AI + automotive knowledge
**Differentiator score**: ⭐⭐⭐⭐⭐

---

#### 12. OBD-II Code Interpretation
**What**: Customer reads error code, AI explains in plain language

**How it works**:
```
Customer: "Ik heb code P0301 uitgelezen"
AI: "Dat is een misfire op cilinder 1. Vaak veroorzaakt door bougies,
     bobine, of injectoren. Bij uw Audi A4 met 120.000 km zou ik
     eerst de bougies controleren. Zal ik een afspraak maken?"
```

**Why unique**: OBD code database + vehicle-specific diagnosis patterns
**Differentiator score**: ⭐⭐⭐⭐

---

#### 13. Proactive Maintenance Calls
**What**: AI calls customers before problems happen

**How it works**:
```
[Outbound call]
AI: "Goedemiddag, u spreekt met de garage. Ik bel omdat uw Volvo
     bijna 90.000 km heeft, en bij dat model is vervanging van de
     distributieriem aangeraden bij 100.000 km.
     Wilt u dit alvast inplannen?"
```

**Why unique**: Predictive maintenance + proactive outbound calling
**Differentiator score**: ⭐⭐⭐⭐⭐

---

#### 14. Insurance Claim Assistant
**What**: Help customer document accident for insurance

**How it works**:
```
Customer: "Ik heb een aanrijding gehad"
AI: "Dat is vervelend. Is iedereen oké?
     Ik kan u helpen met de volgende stappen:
     1. Heeft u foto's gemaakt van de schade?
     2. Heeft u de gegevens van de andere partij?
     3. Zal ik een schade-intake inplannen?
     We kunnen ook helpen met de verzekeringspapieren."
```

**Why unique**: Insurance process knowledge + body shop workflow
**Differentiator score**: ⭐⭐⭐⭐

---

#### 15. Fleet Manager Dashboard
**What**: For garages with business customers (fleet accounts)

**How it works**:
```
Fleet manager calls: "Ik wil de status van al onze bedrijfswagens"
AI: "Uw vloot van 12 voertuigen:
     - 3 staan gepland voor onderhoud deze maand
     - 1 is momenteel in de werkplaats
     - 2 hebben APK die binnen 60 dagen verloopt
     Zal ik het overzicht naar u mailen?"
```

**Why unique**: Fleet management integration + batch operations
**Differentiator score**: ⭐⭐⭐⭐

---

## Part 4: Feature Prioritization Matrix

| Feature | Customer Value | Technical Effort | Uniqueness | Priority |
|---------|---------------|------------------|------------|----------|
| APK Reminder Engine | High | Medium | Very High | P1 |
| Kenteken Intelligence | Very High | Medium | Very High | P1 |
| Service Interval Intelligence | High | Medium | High | P1 |
| Work Order Progress | High | Low | Medium | P1 |
| Smart Symptoms Triage | Medium | Low | High | P2 |
| Intelligent Quotes | High | High | High | P2 |
| Warranty/Recall Check | High | Medium | Very High | P2 |
| Parts ETA | Medium | Medium | Medium | P2 |
| Seasonal Campaigns | Medium | Low | Medium | P3 |
| Loaner Car Booking | Medium | Medium | Medium | P3 |
| Photo Intake | High | High | Very High | P3 |
| OBD Code Interpretation | Medium | Medium | High | P3 |
| Proactive Maintenance Calls | Very High | High | Very High | P3 |
| Insurance Claim Assistant | Medium | Medium | High | P4 |
| Fleet Dashboard | High | High | High | P4 |

---

## Part 5: Competitive Moat Analysis

### What Makes These Features Hard to Copy

| Barrier | Description | Features Protected |
|---------|-------------|-------------------|
| **DMS Integration** | Deep integration with WinCar/garage systems | All customer-specific features |
| **RDW Data** | Dutch vehicle registration database | Kenteken lookup, APK tracking |
| **Automotive Knowledge** | Service intervals, OBD codes, symptoms | Triage, quotes, maintenance |
| **Dutch Context** | APK, winterbanden, local regulations | APK reminders, seasonal |
| **Workflow Understanding** | How garages actually operate | Progress updates, fleet |

### Why Generic AI Can't Compete

A company like Ringly.io or Dialzara would need:
1. ❌ WinCar integration (requires partnership)
2. ❌ RDW API access (requires Dutch entity)
3. ❌ Service interval database (expensive to build)
4. ❌ Dutch automotive regulation knowledge
5. ❌ Understanding of garage workflows

**Time to replicate**: 12-18 months minimum

---

## Part 6: Recommended MVP+ Feature Set

### Phase 1: Current (What We Have)
- [x] Voice calling (Twilio + Web)
- [x] Customer identification
- [x] Work order status
- [x] Parts lookup
- [x] Basic appointment scheduling
- [x] Payment links

### Phase 2: Next 30 Days (Quick Wins)
- [ ] **Kenteken-to-Vehicle Intelligence** (RDW API integration)
- [ ] **Work Order Progress Updates** (real-time status from DMS)
- [ ] **Smart Symptoms Triage** (diagnostic question flows)

### Phase 3: Next 90 Days (Differentiation)
- [ ] **APK Reminder Engine** (proactive outbound calls)
- [ ] **Service Interval Intelligence** (manufacturer data)
- [ ] **Intelligent Quotes** (labor + parts pricing)

### Phase 4: 6+ Months (Innovation)
- [ ] **Warranty/Recall Check** (RDW recall database)
- [ ] **Photo/Video Intake** (WhatsApp + Vision AI)
- [ ] **Proactive Maintenance Calls** (predictive outreach)

---

## Part 7: The "One Feature to Rule Them All"

If I had to pick **ONE feature** that defines our differentiation:

### 🏆 Kenteken Intelligence + Proactive APK Reminders

**Why this combo wins**:

1. **Instant wow factor**: Customer says license plate, we know everything
2. **Revenue generator**: APK reminders create appointments automatically
3. **Hard to replicate**: Requires RDW + DMS + outbound calling
4. **Measurable ROI**: "We booked 47 APK appointments last month via AI"
5. **Dutch-specific**: APK is uniquely Dutch, US competitors can't copy

**The pitch becomes**:
> "Onze AI kent elke auto in Nederland. Zeg je kenteken, en hij weet
> wat je rijdt, wanneer je APK verloopt, en wanneer je onderhoud nodig hebt.
> En hij belt je klanten automatisch als hun APK bijna verloopt."

---

## Summary

### Current State
We have a working voice AI with basic DMS integration. It's functional but not differentiated.

### The Problem
Generic voice AI is everywhere. "We answer your phone with AI" is not a moat.

### The Solution
Build **automotive-specific intelligence** that requires:
- Dutch vehicle data (RDW)
- DMS integration
- Service interval knowledge
- Garage workflow understanding

### Top 3 Features to Build Next
1. **Kenteken Intelligence** - Instant vehicle recognition
2. **APK Reminder Engine** - Proactive revenue generation
3. **Work Order Progress** - Real-time status updates

### The Defensible Position
"We don't just answer calls. We know every car in the Netherlands, when it needs service, and we call your customers before they even think about it."

---

*Document generated by Jan (PM Agent) for GarageAI feature planning.*
