# Licensing and historical releases

> Release-candidate policy, pending copyright-holder and legal review. This
> document explains the intended structure but is not legal advice and does not
> replace the applicable license text.

## Version-specific terms

ASPf-next `0.2.0a1` was released under the MIT License. Rights granted under
that release remain governed by its accompanying MIT License. The exact
historical license is preserved in the
[`v0.2.0a1` tag](https://github.com/dylanflynn477/ASPf-next/blob/v0.2.0a1/LICENSE)
and is not revoked or narrowed by later repository changes.

The public repository also exposed post-release development revisions while
its root license was MIT. To the extent a recipient validly obtained any such
revision under those terms, changing the license now does not revoke that
existing grant. The proposed PolyForm terms govern the new `0.2.0a2` release,
not the revocation of rights in earlier MIT-accompanied copies.

Beginning with version `0.2.0a2`, subsequent releases are proposed to be
distributed under the unmodified
[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0),
with the project's required copyright notice. That license is source available,
is represented by the SPDX identifier `PolyForm-Noncommercial-1.0.0`, and is
not OSI-approved. Releases under it must not be described as open source.

Commercial use, commercial deployment, incorporation into a commercial product
or service, consulting use, or use for commercial advantage requires prior
written permission or a separate commercial license from the copyright holder.

## Why this standard license

PolyForm Noncommercial is the closest established match to the intended public
grant. It permits modification and redistribution for permitted purposes. It
expressly permits personal research, experiment, testing, study, and hobby use
without anticipated commercial application. It also permits use by charitable
organizations, educational institutions, public research organizations, public
safety or health organizations, environmental protection organizations, and
government institutions regardless of funding source or funding obligations.

Using its standard text avoids creating a project-specific public license. A
separate commercial agreement can grant broader rights case by case without
changing the public terms.

## Boundaries requiring written clarification

The public terms should not be paraphrased into permissions they do not clearly
grant. In particular:

- **Internal corporate evaluation:** not clearly permitted when undertaken for
  anticipated commercial advantage. Obtain written permission. If routine
  commercial evaluation is desired, counsel should assess offering PolyForm
  Free Trial as an alternative license.
- **Consulting and contractor use:** ordinarily commercial. A contractor's use
  may also implicate the license's definition of “your company”; the client,
  contractor, and intended deployment should be identified in a written grant.
- **Sponsored academic research:** use by an educational or public research
  institution is expressly permitted regardless of funding obligations, but a
  sponsor's separate use, transfer of derivatives, or commercial deployment is
  not thereby licensed.
- **SaaS and hosted services:** commercial operation or commercial advantage is
  outside the intended public grant, whether or not users receive a copy.
- **Subsidiaries and affiliates:** the license's control-based definition of
  “your company” may group related organizations; do not assume a permission to
  one entity is narrower than that definition without reviewed terms.
- **Redistribution:** permitted only under the license's distribution and
  notice conditions and only for a permitted purpose. Redistribution does not
  convert a later source-available version back to MIT.
- **Mixed personal/commercial intent:** personal use requires no anticipated
  commercial application. Seek written permission when that boundary is
  uncertain.

## Alternatives considered

- **PolyForm Free Trial 1.0.0** adds a standardized, time-limited evaluation
  path, including for prospective commercial users, but does not permit
  distribution. It could be offered as an alternative after legal review if
  commercial evaluation should be automatic rather than permission-based.
- **Business Source License 1.1** permits non-production use and requires each
  version to convert to a GPL-compatible open-source license no later than four
  years after first publication. Its production/non-production boundary and
  mandatory change date do not match an ongoing noncommercial policy as
  closely.
- **Functional Source License 1.1** generally permits commercial uses other
  than competing use and converts to MIT or Apache 2.0 after two years. It is
  substantially broader than the proposed commercial-use restriction.
- **Prosperity Public License 3.0.0** combines noncommercial use with a
  time-limited commercial trial. It is a possible alternative, but PolyForm has
  clearer organization-specific research and education grants and an SPDX
  identifier.
- **PolyForm Internal Use** permits internal business operations and is
  therefore broader than the intended policy. Creative Commons licenses are
  not recommended by Creative Commons for software.

None of these noncommercial or use-restricted choices is an open-source license
under the Open Source Definition, which requires permission for commercial
fields of endeavor.

## Contributor and provenance gate

The pre-release audit found no human contributor identity other than Dylan
Flynn in commits, merged pull requests, co-author trailers, GitHub contributor
data, or repository notices. It found no vendored third-party implementation.
This lowers transition risk but does not prove copyright ownership. Commit
authorship is not a copyright assignment, and employment, contractor, or
tool-assisted-work questions are not resolved by Git metadata.

External patches are paused until a lawyer-reviewed contributor agreement or
copyright-assignment policy is available. The project should not accept a
third-party patch merely on an informal “inbound equals outbound” assumption if
future commercial licensing or relicensing must remain possible.

## Publication checklist

Before publishing `0.2.0a2`, the copyright holder should:

1. obtain legal review of the selected public terms and commercial-licensing
   plan;
2. confirm authority to relicense every post-`0.2.0a1` contribution;
3. decide whether commercial evaluation needs an automatic trial license;
4. provide a durable contact method for permission and commercial licenses;
5. verify repository, package, archive, and release-page metadata; and
6. add a non-destructive note to the `0.2.0a1` GitHub release clarifying that it
   remains MIT-licensed while later versions use different terms.

## Recommended treatment of 0.2.0a1

Retain the `v0.2.0a1` tag and GitHub release. After the later-version terms are
approved, edit only the release description to add this clarification:

> Licensing note: ASPf-next 0.2.0a1 was released under the MIT License and
> remains governed by the MIT License included in this tag. Rights granted for
> this release are unchanged. Later ASPf-next versions may be distributed under
> different terms; consult the license accompanying the specific version you
> use.

Deleting the GitHub release presentation would remove its release-page entry
and any attached assets. It would not erase the Git tag or commits, remove
source archives already obtained, alter downstream copies, or revoke MIT rights
already granted. Rewriting history would likewise not revoke grants already
received for the tagged release or other MIT-accompanied snapshots and is not
proposed.
