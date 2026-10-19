# Investigation Patterns for React + .NET + Angular

This file provides concrete investigation patterns (grep/glob queries) for exploring
codebases during feature analysis. Each pattern set is designed to be delegated to
a cheap explore agent for parallel execution.

---

## .NET Backend Patterns

### Controller Discovery
```
# Find all API controllers
grep: \[ApiController\]
glob: **/*Controller.cs

# Find specific domain controllers
grep: \[Route\("api/{domain}"\)\]
grep: \[Route\(".*{domain}.*"\)\]

# Find endpoint methods
grep: \[Http(Get|Post|Put|Delete|Patch)\].*{domain}
```

### Service Layer Discovery
```
# Find service interfaces
glob: **/I*Service.cs
grep: interface I{Domain}Service

# Find service implementations
grep: class {Domain}Service.*:.*I{Domain}Service
glob: **/*Service.cs

# Find service registration (DI)
grep: services\.(AddScoped|AddTransient|AddSingleton).*{Domain}
grep: builder\.Services\.Add
```

### Domain Model Discovery
```
# Find EF entities
glob: **/Entities/**/*.cs
glob: **/Models/**/*.cs
grep: class {Entity}.*:.*BaseEntity|IAuditable|IEntity

# Find DbContext and DbSets
grep: DbSet<{Entity}>
glob: **/*DbContext.cs
glob: **/*Context.cs

# Find migrations
glob: **/Migrations/**/*.cs
grep: migrationBuilder\.(CreateTable|AddColumn|AlterColumn).*{table}
```

### DTO & Contract Discovery
```
# Find DTOs
glob: **/*Dto.cs
glob: **/*Request.cs
glob: **/*Response.cs
glob: **/*ViewModel.cs
glob: **/Contracts/**/*.cs

# Find AutoMapper profiles
grep: CreateMap<.*{Entity}
glob: **/*Profile.cs
glob: **/*MappingProfile.cs
```

### Validation & Business Rules
```
# FluentValidation
glob: **/*Validator.cs
grep: RuleFor\(.*{Property}

# Data annotations
grep: \[Required\]|\[MaxLength\]|\[Range\]

# Business rule services
grep: class.*{Domain}.*(Rule|Policy|Specification)
```

### Middleware & Cross-Cutting
```
# Auth policies
grep: \[Authorize.*Policy.*=.*"{domain}"\]
grep: options\.AddPolicy\("{domain}"

# Exception handling
glob: **/*ExceptionHandler*.cs
glob: **/*Middleware*.cs

# Configuration
grep: "{Domain}".*:.*\{
glob: **/appsettings*.json
```

### CQRS / MediatR (if applicable)
```
# Commands and Queries
glob: **/*Command.cs
glob: **/*Query.cs
glob: **/*Handler.cs
grep: IRequest<.*{Domain}
grep: IRequestHandler<.*{Domain}
```

---

## React Frontend Patterns

### Component Discovery
```
# Find components by feature
glob: **/{Feature}*.tsx
glob: **/components/**/{feature}*/**
glob: **/pages/**/{feature}*/**
glob: **/features/**/{feature}*/**

# Find component exports
grep: export (default )?(function|const) {Feature}
```

### Hooks & State
```
# Custom hooks
glob: **/hooks/**/*{feature}*.ts
grep: export (function|const) use{Feature}
grep: (useState|useReducer|useContext).*{domain}

# Redux/Zustand/Jotai state
glob: **/store/**/*{feature}*
glob: **/slices/**/*{feature}*
grep: createSlice\(.*name:.*'{feature}'
grep: create\(.*\(set.*get\)  # Zustand pattern

# React Query / TanStack Query
grep: use(Query|Mutation).*{feature}
grep: queryKey.*\[.*'{feature}'
```

### API Layer
```
# API client functions
glob: **/api/**/*{feature}*.ts
glob: **/services/**/*{feature}*.ts
grep: (fetch|axios)\.(get|post|put|delete).*{endpoint}

# API hooks (React Query wrappers)
grep: export.*use.*{Feature}.*(Query|Mutation)

# API types
glob: **/api/**/*{feature}*.types.ts
glob: **/types/**/*{feature}*.ts
```

### Routing
```
# Route definitions
grep: path:.*['"].*{feature}
grep: <Route.*path=.*{feature}
glob: **/routes/**/*.ts*
glob: **/router/**/*.ts*

# Lazy loading
grep: lazy\(\(\).*import\(.*{feature}
grep: React\.lazy
```

### Forms & Validation
```
# Form components
grep: (useForm|useFormik|Formik).*{feature}
glob: **/*{feature}*Form*.tsx

# Validation schemas
grep: (yup|zod|joi).*{feature}
glob: **/*{feature}*.(schema|validation).ts
```

### Testing Patterns
```
# Existing tests
glob: **/{feature}*.test.ts*
glob: **/{feature}*.spec.ts*
glob: **/__tests__/**/{feature}*

# Test utilities
grep: render.*<{Feature}
grep: mock.*{feature}
```

---

## Angular Frontend Patterns

### Component Discovery
```
# Find components
glob: **/{feature}*.component.ts
glob: **/{feature}*.component.html
glob: **/{feature}*.component.scss

# Standalone components
grep: @Component.*standalone.*true.*{feature}
grep: selector:.*'app-{feature}'
```

### Module & Routing
```
# Modules
glob: **/{feature}*.module.ts
grep: @NgModule.*{feature}

# Routing
glob: **/{feature}*-routing.module.ts
glob: **/{feature}*.routes.ts
grep: path:.*'{feature}'
grep: loadChildren.*{feature}
grep: loadComponent.*{feature}
```

### Services & State
```
# Services
glob: **/{feature}*.service.ts
grep: @Injectable.*{feature}

# State management (NgRx)
glob: **/{feature}*.actions.ts
glob: **/{feature}*.reducer.ts
glob: **/{feature}*.effects.ts
glob: **/{feature}*.selectors.ts
glob: **/store/**/{feature}*

# RxJS patterns
grep: (BehaviorSubject|Subject|Observable).*{feature}
```

### Models & Interfaces
```
# Models
glob: **/{feature}*.model.ts
glob: **/{feature}*.interface.ts
glob: **/models/**/{feature}*
glob: **/interfaces/**/{feature}*

# Enums
glob: **/{feature}*.enum.ts
```

### Guards & Interceptors
```
# Route guards
glob: **/{feature}*.guard.ts
grep: canActivate.*{feature}

# HTTP interceptors
glob: **/*interceptor*.ts
grep: intercept.*{feature}
```

### Angular Testing
```
# Tests
glob: **/{feature}*.spec.ts
grep: describe\(.*{Feature}
grep: TestBed.*{feature}
```

---

## Cross-Stack Patterns

### Configuration & Environment
```
# Environment files
glob: **/.env*
glob: **/environment*.ts
glob: **/appsettings*.json
grep: {FEATURE}_.*=

# Feature flags
grep: feature.*flag.*{feature}|{feature}.*feature.*flag
grep: isEnabled\(.*{feature}\)
```

### Shared Types & Contracts
```
# OpenAPI/Swagger
glob: **/swagger*.json
glob: **/*.openapi.*

# Shared type definitions
glob: **/shared/**/*{feature}*
glob: **/common/**/*{feature}*
```

### CI/CD & Infrastructure
```
# Pipeline references
grep: {feature}
glob: **/.github/workflows/**
glob: **/Dockerfile*
glob: **/docker-compose*
```

---

## Investigation Agent Template

When launching an explore agent, construct the prompt using this template:

```
You are investigating the {LAYER} layer of a {TECH} codebase for areas
related to the feature: "{FEATURE_DESCRIPTION}"

Domain keywords: {KEYWORDS}
Related entities: {ENTITIES}

Execute these searches and report ALL findings:

1. [List specific grep/glob patterns from above, substituted with actual values]
2. [...]
3. [...]

For each finding, report:
- File path
- Relevant code snippets (function signatures, class declarations, key logic)
- Patterns observed (naming conventions, folder structure, architectural patterns)
- Potential integration points for the new feature

Also note:
- Any existing partial implementation of similar functionality
- Configuration or environment variables that might be relevant
- Test coverage gaps in the area
```
