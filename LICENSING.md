# Licensing and provenance

The [MIT license](LICENSE) covers Morgan Hough's original contributions to this
fork. It does **not** grant rights to code inherited from another author.

## What the MIT grant covers

The fork's original additions include the `cell_research/` runner and analysis
package, `tests/`, `scripts/execute_notebooks.py`, the three notebooks in
`examples/`, `docs/` and its generated illustrations, and
`modules/multithread/experiment_utils.py`. Original documentation, build
configuration, and workflow additions are also covered.

Original portions of changes to inherited files are offered under MIT only to
the extent of the fork contributor's rights. This is not a license for the whole
modified file's upstream content. Git history records the distinction.

## Inherited sorting implementation

Source: [Zhangtaining/cell_research](https://github.com/Zhangtaining/cell_research),
baseline commit `1fd2bd5921c1f6b423a71f691d5189106a8a1020`.

No upstream license file was present at that baseline. The inherited
`modules/` code, root experiment scripts, `analysis/`, `multi_dimentions/`,
`visualization/`, and other upstream files remain subject to their original
authors' rights. The new runner imports those sorting classes, so the combined
checkout and distribution must not be described as entirely MIT licensed.
Broader reuse of that inherited implementation needs an applicable upstream
permission; this fork does not supply one.

Package metadata expresses this as `MIT AND LicenseRef-Upstream-No-License`.
The custom identifier `LicenseRef-Upstream-No-License` refers to the inherited
material described in this section, for which no upstream license was supplied.
It records that unresolved status; it is not a new permission grant. Both this
document and the scoped MIT notice are included in source and wheel distributions.

To inspect the provenance of a file:

```sh
git diff --name-status 1fd2bd5921c1f6b423a71f691d5189106a8a1020..HEAD
git log --follow -- path/to/file
```

Third-party Python dependencies, cited publications, and any externally supplied
data retain their respective terms. A citation or a public GitHub fork is not a
replacement for an applicable license. See
[GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).
