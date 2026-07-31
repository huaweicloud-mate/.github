# Contributing to huaweicloud-mate

First off, thank you for considering contributing to huaweicloud-mate! 🎉

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

- **Check if the bug has already been reported** — search existing Issues
- **Open a new Issue** — use the Bug Report template, fill in all sections
- **Provide a minimal reproducible example** if possible

### Suggesting Enhancements

- **Check if the enhancement has already been suggested** — search existing Issues
- **Open a new Issue** — use the Feature Request template

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Ensure all tests pass (`npm test`)
5. Commit with a descriptive message following [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat: add new feature`
   - `fix: resolve bug in module`
   - `docs: update README`
6. Push to your fork and open a Pull Request against `main`
7. Wait for review — at least 2 approvals required

## Development Setup

```bash
git clone https://github.com/huaweicloud-mate/huaweicloud-mate.git
cd huaweicloud-mate
npm install
npm run dev
```

## Style Guidelines

- Follow the existing code style in the project
- Run `npm run lint` before submitting — all lint checks must pass
- Write tests for new functionality

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
