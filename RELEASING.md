# Publishing

This repository uses the same release versioning as `denon-rs232`: keep
`version = "0.0.0"` in source and substitute the GitHub release tag during the build.

Configure a PyPI Trusted Publisher (or a pending publisher for the first release):

- PyPI project: `sensecap-lorawan`
- GitHub owner: `balloobbot`
- Repository: `sensecap-lorawan`
- Workflow: `publish.yml`
- Environment: `pypi`

Create the `pypi` GitHub environment. After CI passes, publish a GitHub release
with a plain version tag such as `0.1.0` (without a `v` prefix).
The workflow builds a wheel and source distribution, uploads the artifacts, and
publishes them using GitHub OIDC. No PyPI API token is needed.

```sh
gh release create 0.1.0 --repo balloobbot/sensecap-lorawan \
  --target main --title 0.1.0 --notes-file /path/to/release-notes.md
```

Keep release notes about behavior and supported devices. To retry a failed publish,
rerun the GitHub Actions workflow for that release.
