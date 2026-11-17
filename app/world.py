"""World salary benchmarks and per-country estimates for Placement Intelligence.

IMPORTANT: the figures below are INDICATIVE entry-level benchmarks compiled from general
knowledge (2025-26) and were NOT live-verified against sources. Visa rules and thresholds change
often. Edit COUNTRIES (or replace with your own table) and always confirm on official sites.
"""
from __future__ import annotations

import json, time, urllib.request
from typing import Any

import numpy as np

DATA_AS_OF = "2025-26 indicative benchmarks (not live-verified)"
FX_AS_OF = "2026-11-12 17:43 UTC (x-rates.com)"
# INR per 1 unit of currency
FX_INR = {"USD": 94.04, "CAD": 65.96, "GBP": 124.41, "EUR": 103.94, "AUD": 64.02, "NZD": 52.15,
          "SGD": 73.05, "JPY": 0.5887, "KRW": 0.07036, "MYR": 23.06, "AED": 25.61, "SAR": 25.08,
          "QAR": 25.84, "TWD": 2.849, "CZK": 4.262, "SEK": 9.377, "DKK": 13.90, "NOK": 9.824,
          "PLN": 23.59, "CHF": 112.54, "INR": 1.0}

# iso2, numeric id, name, currency, lat, lon, low, typical, high (annual gross, local),
# monthly living cost incl. rent, tax+social %, visa route, ease 1-5, demand, language, skills, watch-outs
def _c(iso, num, name, cur, lat, lon, lo, ty, hi, live, tax, visa, ease, demand, lang, skills, watch):
    return dict(iso2=iso, id=num, name=name, currency=cur, lat=lat, lon=lon, low=lo, typical=ty, high=hi,
                monthly_living=live, tax_pct=tax, visa=visa, ease=ease, demand=demand, language=lang,
                skills=skills, watch=watch)

COUNTRIES: list[dict[str, Any]] = [
 _c("IN","356","India","INR",20.6,78.9,450000,700000,1200000,40000,8,"No visa needed (home market)",5,"high","English / Hindi",["Data Structures","Java","Python","SQL","Cloud"],
    ["Service-company and product-company offers differ 2-3x for similar profiles.","Check bond, notice-period and variable-pay clauses before signing.","Campus placement offers are usually fixed-CTC; ask for the in-hand split."]),
 _c("US","840","United States","USD",39.8,-98.6,80000,100000,125000,2800,24,"H-1B (lottery + high new-petition fee) or OPT after a US degree",1,"medium","English",["Python","Data Structures","Cloud","Machine Learning","Web Development"],
    ["Direct hiring from India is very hard: H-1B is lottery-based and new petitions carry a large fee; confirm current rules.","Most graduates enter via a US Master's + OPT/STEM OPT.","Big-tech base pay is far above the typical figure shown here."]),
 _c("CA","124","Canada","CAD",56.1,-106.3,60000,72000,88000,2700,24,"Employer-sponsored work permit / Express Entry",2,"medium","English / French",["Python","Cloud","Data Science","Java","DevOps"],
    ["Immigration caps and Express Entry rules change often; check IRCC.","Many Indian grads come via a Canadian diploma + PGWP.","Rent in Toronto/Vancouver eats a big share of pay."]),
 _c("GB","826","United Kingdom","GBP",54.0,-2.5,32000,40000,50000,2200,24,"Skilled Worker visa: sponsor needed, general salary threshold GBP 41,700/yr or the job's going rate (gov.uk, checked 2026-11-15); GBP 33,400 minimum for some reduced-rate cases",3,"medium","English",["Python","Cloud","SQL","Data Science","Java"],
    ["Skilled Worker salary thresholds were raised recently; new-entrant rates are lower. Check gov.uk.","Post-study Graduate route length has been shortened; verify current length.","London pay is higher but so is rent."]),
 _c("IE","372","Ireland","EUR",53.2,-8.0,38000,46000,55000,2400,26,"Critical Skills Employment Permit",3,"high","English",["Cloud","Python","Java","DevOps","Data Science"],
    ["Critical Skills permit has a minimum salary; check current figure.","Dublin rents are among the highest in Europe.","Many global tech EMEA hubs hire here."]),
 _c("DE","276","Germany","EUR",51.2,10.4,48000,55000,65000,1700,36,"EU Blue Card: min gross EUR 50,700/yr, or EUR 45,934/yr for shortage occupations, recent graduates and IT specialists (make-it-in-germany.com, checked 2026-11-15); Opportunity Card to job-hunt",4,"high","English in tech; German helpful",["Java","Python","Cloud","DevOps","C/C++"],
    ["Blue Card needs a minimum salary (lower for shortage occupations like IT).","German is needed outside international tech firms.","Tax + social contributions are high; net is ~35-40% below gross."]),
 _c("NL","528","Netherlands","EUR",52.1,5.3,40000,48000,56000,2000,30,"Highly Skilled Migrant permit (recognised sponsor)",4,"high","English widely used",["Cloud","Python","Java","DevOps","Data Science"],
    ["Employer must be a recognised sponsor.","The 30% tax ruling has been scaled back; confirm current terms.","Housing in Amsterdam is very tight."]),
 _c("FR","250","France","EUR",46.6,2.4,36000,42000,50000,1700,25,"Talent Passport (Salarie qualifie / Blue Card)",3,"medium","French strongly preferred",["Python","Machine Learning","Java","Cloud","Data Science"],
    ["French is often required outside Paris tech firms.","Paperwork is slow; start early.","Salaries are lower than Germany/NL."]),
 _c("AT","040","Austria","EUR",47.5,14.6,40000,46000,54000,1600,28,"Red-White-Red Card (points)",3,"medium","German helpful",["Java","Python","Cloud","C/C++","Data Structures"],
    ["Points-based; German skills add points.","Salary thresholds apply per age band.","Vienna offers good quality of life per euro."]),
 _c("BE","056","Belgium","EUR",50.6,4.7,40000,46000,54000,1700,38,"Single permit / EU Blue Card",3,"medium","Dutch / French helpful",["Java","Python","Cloud","SQL","Data Science"],
    ["Regional rules differ (Flanders/Brussels/Wallonia).","Highest tax wedge in this list.","Multilingual job market."]),
 _c("CH","756","Switzerland","CHF",46.8,8.2,85000,95000,110000,3300,20,"Non-EU work permit (annual quotas)",2,"medium","German / French / English",["Python","Machine Learning","Cloud","Java","DevOps"],
    ["Non-EU quotas are limited; employers must prove no local/EU candidate.","Highest pay but also very high living costs.","Health insurance is mandatory and costly."]),
 _c("SE","752","Sweden","SEK",62.0,15.0,420000,480000,550000,14000,28,"Work permit (salary floor + collective agreement)",3,"high","English widely used",["Python","Cloud","C/C++","Java","DevOps"],
    ["Salary floor for work permits has risen; check Migrationsverket.","Stockholm housing queues are long.","Good English environment in tech."]),
 _c("DK","208","Denmark","DKK",56.0,9.5,400000,460000,540000,11000,37,"Pay Limit / Positive List / Fast-track",3,"high","English widely used",["Python","Cloud","Java","DevOps","Data Science"],
    ["High income tax; check the researcher/key-employee tax scheme.","Pay Limit scheme has a minimum salary.","Copenhagen rents are high."]),
 _c("FI","246","Finland","EUR",64.0,26.0,38000,44000,52000,1700,28,"Specialist residence permit",3,"medium","English in tech",["Python","C/C++","Cloud","Java","Machine Learning"],
    ["Processing times can be long.","Winter + small market; fewer entry-level roles.","Strong embedded/telecom scene."]),
 _c("NO","578","Norway","NOK",61.0,9.0,560000,640000,720000,14000,28,"Skilled worker residence permit",3,"medium","English OK; Norwegian helpful",["Cloud","Java","Python","DevOps","Data Science"],
    ["Pay floor applies for skilled-worker permits.","Oslo is expensive.","Strong energy/maritime tech sector."]),
 _c("PL","616","Poland","PLN",52.0,19.1,90000,115000,145000,5000,24,"Work permit / EU Blue Card",3,"high","English in tech",["Java","Python","Cloud","Web Development","DevOps"],
    ["B2B contracts change tax maths a lot.","Growing outsourcing/R&D hub.","Pay is lower than Western Europe but costs are too."]),
 _c("ES","724","Spain","EUR",40.2,-3.7,26000,32000,40000,1500,22,"Highly Qualified Professional / Blue Card",3,"medium","Spanish helpful",["Python","Java","Cloud","Web Development","Data Science"],
    ["Pay is on the low side for Western Europe.","Spanish is a big advantage outside multinationals.","Barcelona/Madrid have most tech roles."]),
 _c("IT","380","Italy","EUR",42.8,12.6,27000,32000,40000,1500,27,"Work visa via annual quota (decreto flussi)",2,"low","Italian helpful",["Java","Python","C/C++","SQL","Cloud"],
    ["Quota-based and slow.","Lower pay than northern Europe.","Milan has most tech jobs."]),
 _c("PT","620","Portugal","EUR",39.6,-8.0,24000,30000,38000,1400,23,"Work visa / EU Blue Card",3,"medium","English in tech",["Python","Java","Web Development","Cloud","DevOps"],
    ["Immigration rules tightened recently; check current process.","Lisbon rents have climbed fast.","Many outsourcing and remote-friendly roles."]),
 _c("AU","036","Australia","AUD",-25.7,134.5,70000,82000,95000,3200,24,"Skills in Demand / Employer-sponsored visa",3,"medium","English",["Cloud","Python","Java","Web Development","Data Science"],
    ["Visa thresholds and occupation lists change often.","Entry-level roles may be scarce for non-residents.","Sydney/Melbourne rents are high."]),
 _c("NZ","554","New Zealand","NZD",-41.0,172.8,62000,72000,85000,3000,22,"Accredited Employer Work Visa",3,"medium","English",["Web Development","Cloud","Java","Python","DevOps"],
    ["Employer must be accredited; median-wage rules apply.","Small job market.","Great lifestyle, high cost of living."]),
 _c("SG","702","Singapore","SGD",1.35,103.8,54000,66000,80000,3800,10,"Employment Pass: minimum fixed salary S$5,600/month for new applications before 1 Jan 2027, rising to S$6,000 from 1 Jan 2027 (MOM, checked 2026-11-15), plus COMPASS points",2,"medium","English",["Python","Cloud","Java","Machine Learning","DevOps"],
    ["EP minimum salary is relatively high for new grads; check MOM.","COMPASS points scoring applies.","Low tax, but rent is expensive."]),
 _c("JP","392","Japan","JPY",36.2,138.3,3600000,4200000,5000000,190000,20,"Engineer/Specialist visa, Highly Skilled points",3,"medium","Japanese helpful/required",["Java","C/C++","Python","Web Development","Cloud"],
    ["Japanese ability is often required.","Pay is modest in USD terms.","Rent in Tokyo is moderate versus other hubs."]),
 _c("KR","410","South Korea","KRW",36.5,127.9,38000000,45000000,55000000,1900000,15,"E-7 / E-7-4 skilled work visa",3,"medium","Korean required for most roles",["Python","C/C++","Machine Learning","Java","Cloud"],
    ["Korean is needed for most jobs.","E-7 has salary and degree requirements.","Seoul is expensive but pay is rising."]),
 _c("MY","458","Malaysia","MYR",4.2,102.0,48000,66000,90000,3500,11,"Employment Pass (category by salary)",3,"medium","English widely used",["Java","Python","Web Development","Cloud","SQL"],
    ["EP minimum salary was raised; check current category thresholds.","Shared-service centres hire many graduates.","Low living costs relative to pay."]),
 _c("AE","784","United Arab Emirates","AED",24.0,54.0,120000,160000,220000,7500,0,"Employer work permit / Golden Visa",4,"high","English",["Cloud","Python","Web Development","Java","DevOps"],
    ["No personal income tax, but rent in Dubai is high.","Visa tied to employer; check end-of-service benefits.","Verify the employer and contract before travelling."]),
 _c("SA","682","Saudi Arabia","SAR",24.0,45.0,108000,144000,200000,6500,10,"Work visa / Iqama (Saudization quotas apply)",3,"high","English in tech; Arabic helpful",["Cloud","Python","Java","DevOps","Data Science"],
    ["Saudization quotas affect hiring.","Giga-projects drive tech demand.","Check housing/allowances in the offer."]),
 _c("QA","634","Qatar","QAR",25.3,51.2,120000,160000,220000,6000,0,"Employer-sponsored work permit",3,"medium","English / Arabic",["Cloud","Java","Python","Web Development","SQL"],
    ["Small market.","Check contract terms and exit-permit rules.","No income tax."]),
 _c("TW","158","Taiwan","TWD",23.7,121.0,650000,800000,1000000,40000,10,"Employment Gold Card / work permit",3,"medium","Mandarin helpful",["C/C++","Python","Machine Learning","Java","Cloud"],
    ["Semiconductor/hardware focus.","Gold Card has salary criteria; check NDC.","Low cost of living."]),
 _c("CZ","203","Czechia","CZK",49.8,15.5,600000,720000,900000,32000,20,"Employee Card / EU Blue Card",3,"medium","English in tech",["Java","Python","Cloud","Web Development","DevOps"],
    ["Employee Card process is slow.","Prague rents are rising.","Good value hub for central Europe."]),
]
BY_ID = {c["id"]: c for c in COUNTRIES}


def percentile(salary: float, oob: np.ndarray | None) -> float:
    """Mid-rank percentile (0-1) of a predicted salary among out-of-bag predictions."""
    if oob is None or len(oob) == 0:
        return 0.5
    left = np.searchsorted(oob, salary, side="left")
    right = np.searchsorted(oob, salary, side="right")
    return float(np.clip((left + right) / 2 / len(oob), 0.0, 1.0))


def interpolate(c: dict[str, Any], q: float) -> float:
    pts = [(0.0, c["low"] * 0.85), (0.25, c["low"]), (0.5, c["typical"]), (0.75, c["high"]), (1.0, c["high"] * 1.2)]
    for (q0, v0), (q1, v1) in zip(pts, pts[1:]):
        if q <= q1:
            return v0 + (v1 - v0) * (q - q0) / (q1 - q0)
    return pts[-1][1]


def estimate_all(q: float) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for c in COUNTRIES:
        fx = FX_INR[c["currency"]]
        gross = interpolate(c, q)
        net = gross * (1 - c["tax_pct"] / 100)
        savings = net - 12 * c["monthly_living"]
        out[c["id"]] = {
            "gross_local": round(gross), "gross_inr": round(gross * fx),
            "low_inr": round(c["low"] * fx), "typical_inr": round(c["typical"] * fx), "high_inr": round(c["high"] * fx),
            "net_inr": round(net * fx), "savings_inr": round(savings * fx),
            "living_inr_year": round(12 * c["monthly_living"] * fx),
        }
    return out


def public_countries() -> dict[str, Any]:
    return {
        "as_of": DATA_AS_OF, "fx_as_of": FX_AS_OF, "fx_live": _FX_CACHE["live"], "fx_inr": FX_INR, "countries": COUNTRIES,
        "disclaimer": ("Indicative entry-level benchmarks scaled by your resume's percentile in the Indian salary model. "
                       "They are NOT model predictions for these countries, were not live-verified, and visa rules change often. "
                       "Confirm pay, visa thresholds and costs on official sources before deciding."),
    }


_FX_CACHE = {"t": 0.0, "live": False}


def refresh_fx(max_age: float = 6 * 3600) -> bool:
    """Best-effort live exchange-rate refresh (open.er-api.com, no key). Falls back to the static table."""
    global FX_AS_OF
    if time.time() - _FX_CACHE["t"] < max_age:
        return _FX_CACHE["live"]
    _FX_CACHE["t"] = time.time()
    try:
        with urllib.request.urlopen("https://open.er-api.com/v6/latest/INR", timeout=4) as r:
            data = json.load(r)
        rates = data["rates"]
        for cur in list(FX_INR):
            if cur != "INR" and rates.get(cur):
                FX_INR[cur] = round(1 / rates[cur], 6)
        FX_AS_OF = "live, " + str(data.get("time_last_update_utc", "just now"))
        _FX_CACHE["live"] = True
    except Exception:
        _FX_CACHE["live"] = False
    return _FX_CACHE["live"]


OFFICIAL = {"IN": "https://www.india.gov.in", "US": "https://www.uscis.gov/working-in-the-united-states/h-1b-specialty-occupations",
 "CA": "https://www.canada.ca/en/immigration-refugees-citizenship.html", "GB": "https://www.gov.uk/skilled-worker-visa",
 "IE": "https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/", "DE": "https://www.make-it-in-germany.com/en/visa-residence",
 "NL": "https://ind.nl/en/residence-permits/work/highly-skilled-migrant", "FR": "https://france-visas.gouv.fr/en/",
 "AT": "https://www.migration.gv.at/en/", "BE": "https://www.international.belgium.be/en", "CH": "https://www.sem.admin.ch/sem/en/home.html",
 "SE": "https://www.migrationsverket.se/en", "DK": "https://www.nyidanmark.dk/en-GB", "FI": "https://migri.fi/en/home", "NO": "https://www.udi.no/en/",
 "PL": "https://www.gov.pl/", "ES": "https://www.exteriores.gob.es/en", "IT": "https://www.esteri.it/en/", "PT": "https://vistos.mne.gov.pt/en",
 "AU": "https://immi.homeaffairs.gov.au/", "NZ": "https://www.immigration.govt.nz/", "SG": "https://www.mom.gov.sg/passes-and-permits/employment-pass",
 "JP": "https://www.moj.go.jp/isa/index.html", "KR": "https://www.hikorea.go.kr/", "MY": "https://www.imi.gov.my/",
 "AE": "https://u.ae/en/information-and-services/visa-and-emirates-id", "SA": "https://visa.mofa.gov.sa/", "QA": "https://portal.moi.gov.qa/",
 "TW": "https://www.immigration.gov.tw/", "CZ": "https://www.mvcr.cz/mvcr/en/"}
# Visa thresholds checked against official pages on this date; everything else is unverified.
VERIFIED = {"GB": "Visa threshold checked on gov.uk, 2026-11-15", "DE": "Blue Card thresholds checked on make-it-in-germany.com, 2026-11-15",
            "SG": "EP minimum salary checked on mom.gov.sg, 2026-11-15"}
for _c_ in COUNTRIES:
    _c_["official"] = OFFICIAL.get(_c_["iso2"], "")
    _c_["verified"] = VERIFIED.get(_c_["iso2"], "")
