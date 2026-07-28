# EMC / CE Compliance Note - Specter Shield Metal

This note summarizes the electromagnetic compatibility (EMC) status of the Specter Shield Metal Hardware Wallet (Shield board + F469-Discovery + this metal case). It is provided for transparency and does not replace the signed EU Declaration of Conformity, which is issued by the manufacturer and provided with the product.

## Applicable directive and standards

- **EMC Directive 2014/30/EU**
  - EN 55032:2015+A11:2020+A1:2020, Class B (emissions)
  - EN 55035:2017+A11:2020 (immunity)

## Test basis

EMC testing was performed by an independent test house (J. Schmitz GmbH, report no. 259202501, dated 25 November 2025). The device passed emissions and immunity testing, with one exception: under the ESD immunity test (EN 61000-4-2), the device met performance criterion C (temporary malfunction, self-recovering, no data loss, no permanent damage) rather than the target criterion B, at contact discharges of ±4 kV and air discharges of ±8 kV. After such an event the device can be switched back on and functions normally.

## Manufacturer's assessment

The manufacturer assessed this deviation and judged the residual risk acceptable, since the core function of the device - integrity of stored key material - is not affected; the only observed consequence is a temporary restart. Users are advised to ground themselves before handling the device, per the note in the operating manual.

## Declaration of Conformity

The full EU Declaration of Conformity and technical documentation are issued and held by the manufacturer and are provided with the product / available on request. This repository does not include the signed declaration or the full test report.

*This note describes the open-source hardware design for transparency and is not itself a legal declaration of conformity.*
