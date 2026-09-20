# Anonymization checklist

Audit the exact PDF and artifact export that reviewers will receive. This package's neutral text does not make the development repository or its history anonymous. The official policy requires anonymous submissions and artifact access without tracking. [USENIX Security 2027 CFP](https://www.usenix.org/conference/usenixsecurity27/call-for-papers).

## Manuscript

- [ ] Remove author names, affiliations, acknowledgments, funding identifiers, distinctive institutional descriptions, and identifying contact details.
- [ ] Refer to prior work in the third person; handle overlapping and simultaneous work under the CFP rather than omitting relevant citations.
- [ ] Inspect PDF metadata, embedded files, comments, hyperlinks, image metadata, and rendered pages, including appendices.
- [ ] Remove repository owner names, release URLs, badges, public demo links, local paths, and unique project branding that identify the authors.
- [ ] Keep the registration author list and required account details in the submission system, outside reviewer-facing content.

## Artifact export

- [ ] Create a separate snapshot with neutral filenames and no Git history, remotes, CI links, account names, logs containing home directories, or package metadata identifying the authors.
- [ ] Inspect documentation, citation metadata, license headers, notebooks, archives, screenshots, output records, dependency metadata, and hidden files. Resolve license obligations without silently deleting required attribution.
- [ ] Use pseudonymous adjudicator IDs. Remove names, emails, payment records, and annotation-platform account IDs while retaining ratings and disagreement evidence.
- [ ] Inspect outgoing links and redirects as well as visible text. Do not point to the public development repository from the reviewer export.
- [ ] Test the archive and URL in a clean browser session without author credentials. Verify access, downloads, absence of tracking, and the full dependency path.
- [ ] Record a checksum of the exact frozen artifact. Check that the submitted PDF points to that artifact and that access will remain available for the required review period.
- [ ] Have a second reader audit the PDF and export independently; retain their checklist privately.

## Scientific content

- [ ] Preserve model identities, configurations, measurements, evidence provenance, and limitations needed for review. Anonymization must not obscure experimental conditions.
- [ ] Remove submission strategy notes and private operational records from the final artifact. Include the frozen scientific protocol and transparent deviations.
- [ ] Label unavailable evidence honestly; no placeholder result, approval, or artifact URL may look completed.
- [ ] Confirm that earlier public demos or papers are handled consistently with the venue's policies and that searchable public material is not linked as the anonymous artifact.

The audit is pending until every item has evidence and a private reviewer sign-off. No publication, upload, or external message is performed by this checklist.
