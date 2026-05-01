# Informalizer Report: `example.lean`
_Generated on 2026-05-01_

## Summary

This file develops the foundational theory of **symbolic dynamics** — specifically the study of subshifts over general groups — in Lean 4/Mathlib. The mathematical setting is the full shift space $A^G$ (the space of all configurations from a group $G$ to an alphabet $A$), equipped with the product topology, and the main objects of study are closed, shift-invariant subsets called *subshifts*.

### Core constructions

The file begins by defining the **shift action**: `mulShift g x` is the configuration obtained by left-translating `x` by `g` (i.e., $(σ^g x)(h) = x(g \cdot h)$), and establishes that this is a continuous action satisfying the expected algebraic laws ([`mulShift_one`](#obj-mulShift_one), [`mulShift_mul`](#obj-mulShift_mul)). It then introduces **cylinder sets** — the basic open/closed sets in the product topology, consisting of all configurations agreeing with a reference $x$ on a fixed finite window $U$ — and proves they are open (when $A$ is discrete) and closed (when $A$ is T₁). The structures [`Subshift`](#obj-Subshift) and [`MulSubshift`](#obj-MulSubshift) package a carrier set together with proofs of closedness and shift-invariance, and [`mulFullShift`](#obj-mulFullShift) gives the full shift as the universal example. The [`Pattern`](#obj-Pattern) structure encodes a finite partial configuration supported on a finite set, which is the combinatorial data used to define forbidden pattern conditions.

### Language and forbidden-pattern subshifts

The file defines the **language** of a subshift ([`LanguageOn`](#obj-LanguageOn), [`MulSubshift.languageOn`](#obj-MulSubshift-languageOn)) — the collection of finite patterns appearing in some configuration — and the key predicate [`Pattern.mulOccursInAt`](#obj-Pattern-mulOccursInAt), which says that pattern $p$ occurs in configuration $x$ at position $g$. A central lemma ([`mulOccursInAt_eq_cylinder`](#obj-mulOccursInAt_eq_cylinder)) identifies occurrence sets with cylinder sets, making their topological properties immediate. The main construction is `mulForbidden F` and the constructor [`MulSubshift.ofForbidden`](#obj-MulSubshift-ofForbidden): given a family $F$ of forbidden patterns, this produces the subshift of all configurations in which no translate of any pattern in $F$ appears. Shift-invariance of this construction ([`mapsTo_mulShift_mulForbidden`](#obj-mapsTo_mulShift_mulForbidden)) and closedness ([`isClosed_mulForbidden`](#obj-isClosed_mulForbidden)) are proved, the latter by observing that each occurrence set is open (over a discrete alphabet), so each avoidance condition is closed, and the intersection over all patterns and positions is closed.

### How the pieces fit together

The file is organized in a natural dependency order: the shift map and cylinder sets come first as building blocks, then the algebraic/topological lemmas needed for them, then the structural definitions ([`Subshift`](#obj-Subshift), [`Pattern`](#obj-Pattern)), and finally the forbidden-pattern machinery culminating in [`MulSubshift.ofForbidden`](#obj-MulSubshift-ofForbidden). The treatment handles both multiplicative and additive group conventions via Lean's `@[to_additive]` machinery. Together, the results formalize the classical symbolic dynamics theorem that every set of configurations defined by a (possibly infinite) family of forbidden patterns is a subshift — i.e., closed and shift-invariant in the product topology.

---

## Quick Reference

| # | Kind | Name | Summary |
|---|------|------|---------|
| 1 | def | [`mulShift`](#obj-mulShift) | [`mulShift`](#obj-mulShift) is the **left-translation shift** on configurations, in multiplicative notation. |
| 2 | def | [`cylinder`](#obj-cylinder) | This defines a **cylinder set** in the product space `G → A`, where `G` is a group (or index set) and `A` is the alphabet. |
| 3 | lemma | [`mulShift_apply`](#obj-mulShift_apply) | This is a lemma stating that applying the "multiplicative shift" operation of an element `g` to an element `x` yields `g * x`. |
| 4 | lemma | [`mulShift_one`](#obj-mulShift_one) | This lemma states that shifting a function by the identity element (i.e., multiplying the argument by 1) returns the original function unchanged. |
| 5 | lemma | [`mulShift_mul`](#obj-mulShift_mul) | This lemma states that shifting a function $x : G \to A$ by the product $g_1 g_2$ is the same as first shifting by $g_1$ and then shifting the result by $g_2$. |
| 6 | structure | [`Subshift`](#obj-Subshift) | This is a structure packaging the data of a **subshift**: a closed, shift-invariant subset of the full shift space $A^G$, where $A$ is a topological space (the alphabet) and $G$ is an additive monoid (the index group, typically $\mathbb{Z}^d$). |
| 7 | structure | [`MulSubshift`](#obj-MulSubshift) | is a structure that packages together a multiplicative subshift: a closed, shift-invariant subset of a full shift space over an alphabet. |
| 8 | structure | [`Pattern`](#obj-Pattern) | `Pattern A G` represents a finite configuration in the full shift `A^G`, where `A` is the alphabet (with a distinguished default element) and `G` is the index group or set. |
| 9 | lemma | [`continuous_mulShift`](#obj-continuous_mulShift) | This lemma states that the left-translation (shift) map is continuous. |
| 10 | lemma | [`cylinder_eq_set_pi`](#obj-cylinder_eq_set_pi) | This lemma states that a cylinder set on a finite set `U` with basepoint `x : G → A` equals the pi-set over `U` of singleton sets. |
| 11 | lemma | [`mem_cylinder`](#obj-mem_cylinder) | [`mem_cylinder`](#obj-mem_cylinder) characterizes membership in a cylinder set. |
| 12 | def | [`mulFullShift`](#obj-mulFullShift) | is a definition that constructs the **full shift** as an instance of `MulSubshift A G`. |
| 13 | def | [`fromConfig`](#obj-fromConfig) | This is a definition that constructs a `Pattern A G` from a configuration `x : G → A` by restricting it to a finite subset `U : Finset G`. |
| 14 | lemma | [`finite_setOf_pattern_support_eq`](#obj-finite_setOf_pattern_support_eq) | This lemma states that for any finset $U \subseteq G$, the collection of patterns with support exactly equal to $U$ is a finite set. |
| 15 | lemma | [`isOpen_cylinder`](#obj-isOpen_cylinder) | This lemma states that cylinder sets are open when the alphabet `A` carries the discrete topology. |
| 16 | lemma | [`isClosed_cylinder`](#obj-isClosed_cylinder) | This lemma states that in a product space $A^G$ (functions from $G$ to $A$), every cylinder set is closed whenever $A$ is a T1 space. |
| 17 | def | [`Pattern.mulShift`](#obj-Pattern-mulShift) | This is a noncomputable definition that translates a finite pattern `p` (supported on a finite subset of a group `G` with values in `A`) so that it "occurs at position `v`" within a full configuration `G → A`. |
| 18 | def | [`LanguageOn`](#obj-LanguageOn) | `LanguageOn X U` is the *language* of a set of configurations `X` on a finite shape `U`. |
| 19 | def | [`mulForbidden`](#obj-mulForbidden) | A definition that constructs a *shift space* (subshift) from a set of forbidden patterns. |
| 20 | lemma | [`mulShift_apply_mul_left_of_mem`](#obj-mulShift_apply_mul_left_of_mem) | This lemma states that the left-shifted pattern `p.mulShift v` recovers the original pattern's configuration at translated support points. |
| 21 | def | [`MulSubshift.languageOn`](#obj-MulSubshift-languageOn) | `MulSubshift.languageOn Y U` is the *language of the subshift `Y` restricted to the finite shape `U`*: it is the set of all patterns with support `U` that appear in the subshift `Y`. |
| 22 | def | [`Pattern.mulOccursInAt`](#obj-Pattern-mulOccursInAt) | [`Pattern.mulOccursInAt`](#obj-Pattern-mulOccursInAt) is a predicate asserting that a finite pattern `p` occurs in a configuration `x : G → A` at position `g : G`. |
| 23 | lemma | [`mulOccursInAt_eq_cylinder`](#obj-mulOccursInAt_eq_cylinder) | This lemma characterizes the **occurrence set** of a pattern at a position as a cylinder set. |
| 24 | lemma | [`mulOccursInAt_mulShift`](#obj-mulOccursInAt_mulShift) | This lemma states that shifting a configuration and checking pattern occurrences commute in a precise sense. |
| 25 | lemma | [`isOpen_mulOccursInAt`](#obj-isOpen_mulOccursInAt) | This lemma states that for a pattern `p` on a group `G` with alphabet `A` (equipped with the discrete topology), the set of configurations in which the pattern `p` occurs at position `g` is an open set. |
| 26 | lemma | [`mapsTo_mulShift_mulForbidden`](#obj-mapsTo_mulShift_mulForbidden) | This lemma states that the set of configurations avoiding a family `F` of patterns is closed under multiplication shifts. |
| 27 | lemma | [`isClosed_mulForbidden`](#obj-isClosed_mulForbidden) | This lemma states that when `A` carries the discrete topology, the set `mulForbidden F` of colorings `G → A` that avoid every pattern in the family `F` is a closed subset of the product topology on `G → A`. |
| 28 | def | [`MulSubshift.ofForbidden`](#obj-MulSubshift-ofForbidden) | This is a constructor for multiplicative subshifts defined by **forbidden patterns**. |
| 29 | lemma | [`isClosed_mulOccursInAt`](#obj-isClosed_mulOccursInAt) | This lemma states that for a pattern `p` and group element `g`, the set of points `x` where the pattern `p` occurs (multiplicatively) at position `g` is a closed subset of `A`, provided the ambient space `A` is a T₁ topological space. |

---

## Objects (Dependency Order)

<a id="obj-mulShift"></a>
### 1. [def] [`mulShift`](#obj-mulShift) _(lines 151–153)_

_[`mulShift`](#obj-mulShift) is the **left-translation shift** on configurations, in multiplicative notation._

<details>
<summary>View details</summary>

**Signature:**
```lean
def mulShift (g : G) (x : G → A) : G → A
```

**Kind:** Definition

[`mulShift`](#obj-mulShift) is the **left-translation shift** on configurations, in multiplicative notation. Given a group (or monoid) element `g : G` and a configuration `x : G → A`, the shifted configuration `mulShift g x : G → A` is defined by

$$(\text{mulShift}\, g\, x)(h) = x(g \cdot h).$$

Intuitively, the value at position `h` in the shifted configuration is the value that was at position `g \cdot h` in the original one. This defines a left action of `G` on the set of configurations `G → A` by precomposition with left multiplication.

</details>

---

<a id="obj-cylinder"></a>
### 2. [def] [`cylinder`](#obj-cylinder) _(lines 195–200)_

_This defines a **cylinder set** in the product space `G → A`, where `G` is a group (or index set) and `A` is the alphabet._

<details>
<summary>View details</summary>

**Signature:**
```lean
def cylinder (U : Finset G) (x : G → A) : Set (G → A)
```

**Kind:** Definition

This defines a **cylinder set** in the product space `G → A`, where `G` is a group (or index set) and `A` is the alphabet. Given a finite subset `U : Finset G` and a reference configuration `x : G → A`, the cylinder set consists of all configurations `y : G → A` that agree with `x` on every index in `U`, i.e., `{y | ∀ g ∈ U, y g = x g}`.

Cylinder sets are fundamental in symbolic dynamics and the theory of product spaces: when `A` carries the discrete topology, they form a basis of clopen sets for the product (Tychonoff) topology on `G → A`, and every open set is a union of cylinders.

</details>

---

<a id="obj-mulShift_apply"></a>
### 3. [lemma] [`mulShift_apply`](#obj-mulShift_apply) _(lines 154–156)_

_This is a lemma stating that applying the "multiplicative shift" operation of an element `g` to an element `x` yields `g * x`._

<details>
<summary>View details</summary>

**Signature:**
```lean
@[to_additive (attr
```

This is a lemma stating that applying the "multiplicative shift" operation of an element `g` to an element `x` yields `g * x`. In other words, if `mulShift g` denotes the map defined by left-multiplication by `g`, then `mulShift g x = g * x`. This is essentially the defining equation (the "apply" or "beta-reduction" lemma) confirming that the construction does what it says on the tin.

</details>

---

<a id="obj-mulShift_one"></a>
### 4. [lemma] [`mulShift_one`](#obj-mulShift_one) _(lines 157–160)_

_This lemma states that shifting a function by the identity element (i.e., multiplying the argument by 1) returns the original function unchanged._

<details>
<summary>View details</summary>

**Signature:**
```lean
@[to_additive (attr
```

**Lemma: [`mulShift_one`](#obj-mulShift_one)**

This lemma states that shifting a function by the identity element (i.e., multiplying the argument by 1) returns the original function unchanged. Formally, `mulShift f 1 = f`, where `mulShift f g` denotes the function `x ↦ f (x * g)` (or the additive analogue `x ↦ f (x + 0)` via the `to_additive` attribute). This is an immediate consequence of the fact that multiplying by 1 (or adding 0) is the identity operation in a monoid.

</details>

---

<a id="obj-mulShift_mul"></a>
### 5. [lemma] [`mulShift_mul`](#obj-mulShift_mul) _(lines 161–167)_

_This lemma states that shifting a function $x : G \to A$ by the product $g_1 g_2$ is the same as first shifting by $g_1$ and then shifting the result by $g_2$._

<details>
<summary>View details</summary>

**Signature:**
```lean
@[to_additive] lemma mulShift_mul (g₁ g₂ : G) (x : G → A) :
    mulShift (g₁ * g₂) x = mulShift g₂ (mulShift g₁ x)
```

This lemma states that shifting a function $x : G \to A$ by the product $g_1 g_2$ is the same as first shifting by $g_1$ and then shifting the result by $g_2$. In other words, the action of $G$ on functions $G \to A$ by left-translation is compatible with the group multiplication: $\text{mulShift}(g_1 g_2)(x) = \text{mulShift}(g_2)(\text{mulShift}(g_1)(x))$. The `@[to_additive]` attribute generates the analogous result for additive groups automatically.

</details>

---

<a id="obj-Subshift"></a>
### 6. [structure] [`Subshift`](#obj-Subshift) _(lines 230–249)_

_This is a structure packaging the data of a **subshift**: a closed, shift-invariant subset of the full shift space $A^G$, where $A$ is a topological space (the alphabet) and $G$ is an additive monoid (the index group, typically $\mathbb{Z}^d$)._

<details>
<summary>View details</summary>

**Signature:**
```lean
structure Subshift (A : Type*) [TopologicalSpace A] (G : Type*) [AddMonoid G]
```

This is a structure packaging the data of a **subshift**: a closed, shift-invariant subset of the full shift space $A^G$, where $A$ is a topological space (the alphabet) and $G$ is an additive monoid (the index group, typically $\mathbb{Z}^d$).

Concretely, a `Subshift A G` consists of three pieces:
1. A **carrier set** of configurations $G \to A$ (the "allowed" configurations),
2. A proof that the carrier is **closed** in the product topology on $A^G$,
3. A proof that the carrier is **shift-invariant**: for every $g \in G$, the left-translation shift $\sigma^g$ maps the carrier into itself.

This captures the standard symbolic dynamics definition: a subshift is a closed subspace of $A^G$ that is invariant under all shifts $(\sigma^g f)(h) = f(g + h)$.

</details>

---

<a id="obj-MulSubshift"></a>
### 7. [structure] [`MulSubshift`](#obj-MulSubshift) _(lines 250–268)_

_is a structure that packages together a multiplicative subshift: a closed, shift-invariant subset of a full shift space over an alphabet._

<details>
<summary>View details</summary>

**Signature:**
```lean
structure MulSubshift
```

**MulSubshift** is a structure that packages together a multiplicative subshift: a closed, shift-invariant subset of a full shift space over an alphabet. Concretely, it bundles a set of bi-infinite (or one-sided) sequences over some alphabet together with the data witnessing that this set is closed under the shift map and is topologically closed (or satisfies the relevant subshift conditions in the multiplicative/symbolic dynamics setting). This is the multiplicative-convention analogue of a subshift, where the group action on sequence spaces is written multiplicatively rather than additively.

</details>

---

<a id="obj-Pattern"></a>
### 8. [structure] [`Pattern`](#obj-Pattern) _(lines 286–317)_

_`Pattern A G` represents a finite configuration in the full shift `A^G`, where `A` is the alphabet (with a distinguished default element) and `G` is the index group or set._

<details>
<summary>View details</summary>

**Signature:**
```lean
structure Pattern (A : Type*) (G : Type*) [Inhabited A]
```

**Kind:** Structure

`Pattern A G` represents a finite configuration in the full shift `A^G`, where `A` is the alphabet (with a distinguished default element) and `G` is the index group or set. It packages three pieces of data:

1. **`config : G → A`** — a full configuration on `G`;
2. **`support : Finset G`** — a finite subset of coordinates (the "support" of the pattern);
3. **`condition`** — a proof that `config g = default` for all `g ∉ support`.

Mathematically, this encodes a *partial* configuration that specifies values on finitely many coordinates and takes the default value everywhere else. Each pattern corresponds to a **cylinder set**: the set of all full configurations `x : G → A` that agree with `config` on `support`. Patterns are used as forbidden configurations to define subshifts — closed, shift-invariant subsets of the full shift `A^G`.

</details>

---

<a id="obj-continuous_mulShift"></a>
### 9. [lemma] [`continuous_mulShift`](#obj-continuous_mulShift) _(lines 168–194)_

_This lemma states that the left-translation (shift) map is continuous._

<details>
<summary>View details</summary>

**Signature:**
```lean
@[to_additive (attr
```

**Lemma: [`continuous_mulShift`](#obj-continuous_mulShift)**

This lemma states that the left-translation (shift) map is continuous. Specifically, for a topological group, the function that left-multiplies by a fixed element — sending $x \mapsto a \cdot x$ for some fixed $a$ — is a continuous map.

</details>

---

<a id="obj-cylinder_eq_set_pi"></a>
### 10. [lemma] [`cylinder_eq_set_pi`](#obj-cylinder_eq_set_pi) _(lines 201–204)_

_This lemma states that a cylinder set on a finite set `U` with basepoint `x : G → A` equals the pi-set over `U` of singleton sets._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma cylinder_eq_set_pi (U : Finset G) (x : G → A) :
    cylinder U x = Set.pi (↑U : Set G) (fun i => ({x i} : Set A))
```

This lemma states that a cylinder set on a finite set `U` with basepoint `x : G → A` equals the pi-set over `U` of singleton sets. Concretely, it is the set of all functions `f : G → A` that agree with `x` on every index in `U`, expressed as the product $\prod_{i \in U} \{x(i)\}$ viewed as a subset of $G \to A$.

</details>

---

<a id="obj-mem_cylinder"></a>
### 11. [lemma] [`mem_cylinder`](#obj-mem_cylinder) _(lines 205–210)_

_[`mem_cylinder`](#obj-mem_cylinder) characterizes membership in a cylinder set._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mem_cylinder {U : Finset G} {x y : G → A} :
    y ∈ cylinder U x ↔ ∀ i ∈ U, y i = x i
```

**Lemma:** [`mem_cylinder`](#obj-mem_cylinder) characterizes membership in a cylinder set.

An element `y : G → A` belongs to the cylinder `cylinder U x` (centered at `x` with base finite set `U ⊆ G`) if and only if `y` agrees with `x` on every index in `U`, i.e., `y i = x i` for all `i ∈ U`. This is the standard definition of a cylinder set in a product space, where membership is determined by finitely many coordinates.

</details>

---

<a id="obj-mulFullShift"></a>
### 12. [def] [`mulFullShift`](#obj-mulFullShift) _(lines 269–285)_

_is a definition that constructs the **full shift** as an instance of `MulSubshift A G`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def mulFullShift (A G) [TopologicalSpace A] [Monoid G] : MulSubshift A G where
  carrier
```

**[`mulFullShift`](#obj-mulFullShift)** is a definition that constructs the **full shift** as an instance of `MulSubshift A G`. It is the multiplicative subshift on alphabet `A` over the monoid `G` whose carrier set consists of *all* configurations `G → A` — that is, no patterns are forbidden and every function from the index monoid `G` to the alphabet `A` is included. This is the largest possible subshift, serving as the ambient space from which other subshifts are carved out by forbidding certain patterns.

</details>

---

<a id="obj-fromConfig"></a>
### 13. [def] [`fromConfig`](#obj-fromConfig) _(lines 391–411)_

_This is a definition that constructs a `Pattern A G` from a configuration `x : G → A` by restricting it to a finite subset `U : Finset G`._

<details>
<summary>View details</summary>

**Signature:**
```lean
noncomputable def fromConfig (x : G → A) (U : Finset G) : Pattern A G
```

This is a definition that constructs a `Pattern A G` from a configuration `x : G → A` by restricting it to a finite subset `U : Finset G`. The resulting pattern agrees with `x` on elements of `U`, takes the default value of `A` outside `U`, and has support exactly `U`. Intuitively, it captures the "local snapshot" of the configuration `x` on the finite window `U`, filling in a canonical placeholder value everywhere else.

</details>

---

<a id="obj-finite_setOf_pattern_support_eq"></a>
### 14. [lemma] [`finite_setOf_pattern_support_eq`](#obj-finite_setOf_pattern_support_eq) _(lines 586–615)_

_This lemma states that for any finset $U \subseteq G$, the collection of patterns with support exactly equal to $U$ is a finite set._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma finite_setOf_pattern_support_eq
    {A G : Type*} [Finite A] [Inhabited A]
    (U : Finset G) :
    ({p : Pattern A G | p.support = U}).Finite
```

This lemma states that for any finset $U \subseteq G$, the collection of patterns with support exactly equal to $U$ is a finite set. Here a pattern is a function-like object over an alphabet $A$ and group $G$, and its support is the finite set of group elements where it is "active." The finiteness follows because $A$ is a finite type, so there are only finitely many ways to assign alphabet values on the finite domain $U$.

</details>

---

<a id="obj-isOpen_cylinder"></a>
### 15. [lemma] [`isOpen_cylinder`](#obj-isOpen_cylinder) _(lines 211–215)_

_This lemma states that cylinder sets are open when the alphabet `A` carries the discrete topology._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isOpen_cylinder [DiscreteTopology A] (U : Finset G) (x : G → A) :
    IsOpen (cylinder U x)
```

This lemma states that cylinder sets are open when the alphabet `A` carries the discrete topology. Specifically, given a finite set `U` of indices in `G` and a configuration `x : G → A`, the cylinder set consisting of all functions `G → A` that agree with `x` on `U` is open in the product topology. This holds because a cylinder is a basic open set in the product topology — it is a finite intersection of preimages of singletons under coordinate projections, and singletons are open in a discrete space.

</details>

---

<a id="obj-isClosed_cylinder"></a>
### 16. [lemma] [`isClosed_cylinder`](#obj-isClosed_cylinder) _(lines 216–229)_

_This lemma states that in a product space $A^G$ (functions from $G$ to $A$), every cylinder set is closed whenever $A$ is a T1 space._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isClosed_cylinder [T1Space A] (U : Finset G) (x : G → A) :
    IsClosed (cylinder U x)
```

This lemma states that in a product space $A^G$ (functions from $G$ to $A$), every cylinder set is closed whenever $A$ is a T1 space. A cylinder set `cylinder U x` consists of all functions $f : G \to A$ that agree with $x$ on the finite set $U \subseteq G$, i.e., $\{f \mid \forall i \in U,\ f(i) = x(i)\}$. The T1 hypothesis is needed because the cylinder is an intersection of preimages of singletons $\{x(i)\}$ under the coordinate projections, and singletons are closed in a T1 space.

</details>

---

<a id="obj-Pattern-mulShift"></a>
### 17. [def] [`Pattern.mulShift`](#obj-Pattern-mulShift) _(lines 373–390)_

_This is a noncomputable definition that translates a finite pattern `p` (supported on a finite subset of a group `G` with values in `A`) so that it "occurs at position `v`" within a full configuration `G → A`._

<details>
<summary>View details</summary>

**Signature:**
```lean
protected noncomputable def Pattern.mulShift (p : Pattern A G) (v : G) : G → A
```

This is a noncomputable definition that translates a finite pattern `p` (supported on a finite subset of a group `G` with values in `A`) so that it "occurs at position `v`" within a full configuration `G → A`.

Given a group element `h : G`, the output is determined as follows: if `h` belongs to the left-translate `v + p.support` of the pattern's support, noncomputably choose some `w` in `p.support` satisfying `v + w = h` and return the pattern's value `p.config w`; otherwise, return the default value of `A`. The result is a global configuration `G → A` that looks like the pattern `p` shifted by `v`, padded with defaults outside the translated support.

Because `G` is not assumed to be left-cancellative, the chosen preimage `w` may not be unique, so this definition is only well-behaved (independent of the noncomputable choice) under a left-cancellation hypothesis, which is handled in separate lemmas.

</details>

---

<a id="obj-LanguageOn"></a>
### 18. [def] [`LanguageOn`](#obj-LanguageOn) _(lines 616–619)_

_`LanguageOn X U` is the *language* of a set of configurations `X` on a finite shape `U`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def LanguageOn (X : Set (G → A)) (U : Finset G) : Set (Pattern A G)
```

**Definition.** `LanguageOn X U` is the *language* of a set of configurations `X` on a finite shape `U`. Specifically, it is the set of all patterns (functions `U → A`) obtained by restricting some configuration `x ∈ X` to the finite set `U`. In other words, a pattern `p` belongs to `LanguageOn X U` if and only if there exists a configuration `x ∈ X` such that `p` is `x` restricted to `U`.

</details>

---

<a id="obj-mulForbidden"></a>
### 19. [def] [`mulForbidden`](#obj-mulForbidden) _(lines 338–372)_

_A definition that constructs a *shift space* (subshift) from a set of forbidden patterns._

<details>
<summary>View details</summary>

**Signature:**
```lean
def mulForbidden (F : Set (Pattern A G)) : Set (G → A)
```

**What it is:** A definition that constructs a *shift space* (subshift) from a set of forbidden patterns.

**Mathematical content:** Given a set `F` of patterns (finite partial configurations on an alphabet `A` indexed by a group `G`), `mulForbidden F` is the set of all *configurations* `x : G → A` such that no pattern `p ∈ F` appears in `x` at any position `g : G`. A pattern `p` is said to *occur* in `x` at position `g` if the translate of `p` by `g` matches `x` on the relevant coordinates. The result is the subshift defined by forbidding exactly the patterns in `F`.

**In short:** This is the standard construction `X_F = \{ x \in A^G : \text{no translate of any } p \in F \text{ appears in } x \}$, realizing the classical notion of a shift of finite type (or sofic shift, depending on `F`) in the multiplicative group setting.

</details>

---

<a id="obj-mulShift_apply_mul_left_of_mem"></a>
### 20. [lemma] [`mulShift_apply_mul_left_of_mem`](#obj-mulShift_apply_mul_left_of_mem) _(lines 412–440)_

_This lemma states that the left-shifted pattern `p.mulShift v` recovers the original pattern's configuration at translated support points._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mulShift_apply_mul_left_of_mem
    (p : Pattern A G) (v w : G) (hw : w ∈ p.support) :
    p.mulShift v (v * w) = p.config w
```

This lemma states that the left-shifted pattern `p.mulShift v` recovers the original pattern's configuration at translated support points. Specifically, if `w` is in the support of a pattern `p`, then evaluating the shifted pattern at the translated site `v * w` gives the same value as evaluating the original configuration at `w`. Intuitively, shifting the pattern by `v` and then querying at `v * w` "undoes" the shift, since `v * w` is the unique preimage of itself under left-multiplication by `v` (using left-cancellability of `G`).

</details>

---

<a id="obj-MulSubshift-languageOn"></a>
### 21. [def] [`MulSubshift.languageOn`](#obj-MulSubshift-languageOn) _(lines 620–628)_

_`MulSubshift.languageOn Y U` is the *language of the subshift `Y` restricted to the finite shape `U`*: it is the set of all patterns with support `U` that appear in the subshift `Y`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def MulSubshift.languageOn {A G} [TopologicalSpace A] [Inhabited A] [Monoid G]
    (Y : MulSubshift A G) (U : Finset G) : Set (Pattern A G)
```

**Definition.** `MulSubshift.languageOn Y U` is the *language of the subshift `Y` restricted to the finite shape `U`*: it is the set of all patterns with support `U` that appear in the subshift `Y`. Concretely, it collects all `Pattern A G` (functions `U → A`, essentially) that arise as the restriction of some configuration in `Y` to the finite index set `U ⊆ G`.

</details>

---

<a id="obj-Pattern-mulOccursInAt"></a>
### 22. [def] [`Pattern.mulOccursInAt`](#obj-Pattern-mulOccursInAt) _(lines 318–337)_

_[`Pattern.mulOccursInAt`](#obj-Pattern-mulOccursInAt) is a predicate asserting that a finite pattern `p` occurs in a configuration `x : G → A` at position `g : G`._

<details>
<summary>View details</summary>

**Signature:**
```lean
def Pattern.mulOccursInAt (p : Pattern A G) (x : G → A) (g : G) : Prop
```

[`Pattern.mulOccursInAt`](#obj-Pattern-mulOccursInAt) is a predicate asserting that a finite pattern `p` occurs in a configuration `x : G → A` at position `g : G`. Concretely, it requires that for every position `h` in the support of `p`, the value `x(g \cdot h)$ (or $x(g + h)$ in additive notation) equals the prescribed value `p.config(h)`. This is the fundamental notion of pattern occurrence used to define subshifts: a configuration belongs to a subshift defined by forbidden patterns precisely when none of those patterns occurs at any position.

</details>

---

<a id="obj-mulOccursInAt_eq_cylinder"></a>
### 23. [lemma] [`mulOccursInAt_eq_cylinder`](#obj-mulOccursInAt_eq_cylinder) _(lines 489–516)_

_This lemma characterizes the **occurrence set** of a pattern at a position as a cylinder set._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mulOccursInAt_eq_cylinder
    (p : Pattern A G) (g : G) :
    { x | p.mulOccursInAt x g } = cylinder (p.support.image (g * ·)) (p.mulShift g)
```

This lemma characterizes the **occurrence set** of a pattern at a position as a cylinder set.

Concretely, given a pattern `p : Pattern A G` and a group element `g : G`, the set of configurations `x` in which `p` occurs at position `g` equals the cylinder defined by: the support window `p.support.image (g * ·)` (i.e., the support of `p` translated left by `g`), and the values prescribed by the translated pattern `p.mulShift g`. In other words, `p` occurs at position `g` in configuration `x` if and only if `x` agrees with the `g`-translate of `p` on every site of the form `g * w` for `w` in the support of `p`. The proof uses left-cancellation in `G` to identify the translated support unambiguously.

</details>

---

<a id="obj-mulOccursInAt_mulShift"></a>
### 24. [lemma] [`mulOccursInAt_mulShift`](#obj-mulOccursInAt_mulShift) _(lines 441–454)_

_This lemma states that shifting a configuration and checking pattern occurrences commute in a precise sense._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mulOccursInAt_mulShift {A G : Type*} [Inhabited A] [Monoid G]
    (p : Pattern A G) (x : G → A) (g h : G) :
    p.mulOccursInAt (mulShift g x) h ↔ p.mulOccursInAt x (g * h)
```

This lemma states that shifting a configuration and checking pattern occurrences commute in a precise sense. Specifically, a pattern `p` occurs at position `h` in the `g`-shifted configuration `mulShift g x` if and only if `p` occurs at position `g * h` in the original configuration `x`. In other words, applying a left-multiplication shift by `g` to the configuration moves the reference point for occurrences by the same group element `g` on the right of the position.

</details>

---

<a id="obj-isOpen_mulOccursInAt"></a>
### 25. [lemma] [`isOpen_mulOccursInAt`](#obj-isOpen_mulOccursInAt) _(lines 517–531)_

_This lemma states that for a pattern `p` on a group `G` with alphabet `A` (equipped with the discrete topology), the set of configurations in which the pattern `p` occurs at position `g` is an open set._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isOpen_mulOccursInAt [DiscreteTopology A] (p : Pattern A G) (g : G) :
    IsOpen { x | p.mulOccursInAt x g }
```

This lemma states that for a pattern `p` on a group `G` with alphabet `A` (equipped with the discrete topology), the set of configurations in which the pattern `p` occurs at position `g` is an open set. In other words, the property of a configuration containing a particular translate of the pattern at a given group element `g` is an open condition in the product topology on the configuration space. This is expected because the occurrence of a pattern at a fixed location depends only on finitely many coordinates (the support of the pattern), and cylinder sets defined by finitely many constraints on discrete fibers are open in the product topology.

</details>

---

<a id="obj-mapsTo_mulShift_mulForbidden"></a>
### 26. [lemma] [`mapsTo_mulShift_mulForbidden`](#obj-mapsTo_mulShift_mulForbidden) _(lines 455–488)_

_This lemma states that the set of configurations avoiding a family `F` of patterns is closed under multiplication shifts._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma mapsTo_mulShift_mulForbidden {A G : Type*} [Inhabited A] [Monoid G]
    (F : Set (Pattern A G)) (h : G) :
    Set.MapsTo (mulShift h) (mulForbidden (A
```

This lemma states that the set of configurations avoiding a family `F` of patterns is closed under multiplication shifts. Specifically, if a configuration `x` (a function on a group `G` taking values in an alphabet `A`) avoids every pattern `p ∈ F`, then the shifted configuration `mulShift h x` (which precomposes `x` with left-multiplication by `h`) also avoids every pattern in `F`. In other words, `mulShift h` maps `mulForbidden F` into itself, making pattern avoidance a shift-invariant property.

</details>

---

<a id="obj-isClosed_mulForbidden"></a>
### 27. [lemma] [`isClosed_mulForbidden`](#obj-isClosed_mulForbidden) _(lines 532–548)_

_This lemma states that when `A` carries the discrete topology, the set `mulForbidden F` of colorings `G → A` that avoid every pattern in the family `F` is a closed subset of the product topology on `G → A`._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isClosed_mulForbidden [DiscreteTopology A] (F : Set (Pattern A G)) :
    IsClosed (mulForbidden F)
```

This lemma states that when `A` carries the discrete topology, the set `mulForbidden F` of colorings `G → A` that avoid every pattern in the family `F` is a closed subset of the product topology on `G → A`.

The proof strategy is visible from the docstring: each set of colorings where a specific pattern `p` occurs at a specific location `v` is open (since `A` is discrete, occurrence is determined by finitely many point conditions, each open). Therefore its complement — colorings where `p` does *not* occur at `v` — is closed, and `mulForbidden F` is the intersection of all such closed sets over all `p ∈ F` and all `v ∈ G`, hence closed.

</details>

---

<a id="obj-MulSubshift-ofForbidden"></a>
### 28. [def] [`MulSubshift.ofForbidden`](#obj-MulSubshift-ofForbidden) _(lines 573–585)_

_This is a constructor for multiplicative subshifts defined by **forbidden patterns**._

<details>
<summary>View details</summary>

**Signature:**
```lean
def MulSubshift.ofForbidden [DiscreteTopology A] (F : Set (Pattern A G)) : MulSubshift A G where
  carrier
```

This is a constructor for multiplicative subshifts defined by **forbidden patterns**. Given a discrete alphabet `A`, a group `G`, and a family `F` of forbidden patterns, `MulSubshift.ofForbidden F` produces the subshift consisting of all configurations `x : G → A` in which no pattern from `F` occurs at any position.

The three required properties of a subshift are verified automatically:
- **Carrier**: the set of `F`-avoiding configurations,
- **Closedness**: each "occurrence set" (configurations where a specific pattern appears at a specific location) is open in the product topology, so its complement is closed, and finite intersections/unions give that the avoiding set is closed,
- **Shift-invariance**: if a configuration avoids all patterns in `F`, so does any shift of it, since shifting merely relabels positions.

This is one of the most fundamental ways to construct subshifts, generalizing the classical symbolic dynamics notion that a subshift of finite type (SFT) is defined by a finite forbidden list.

</details>

---

<a id="obj-isClosed_mulOccursInAt"></a>
### 29. [lemma] [`isClosed_mulOccursInAt`](#obj-isClosed_mulOccursInAt) _(lines 549–572)_

_This lemma states that for a pattern `p` and group element `g`, the set of points `x` where the pattern `p` occurs (multiplicatively) at position `g` is a closed subset of `A`, provided the ambient space `A` is a T₁ topological space._

<details>
<summary>View details</summary>

**Signature:**
```lean
lemma isClosed_mulOccursInAt [T1Space A] (p : Pattern A G) (g : G) :
    IsClosed { x | p.mulOccursInAt x g }
```

This lemma states that for a pattern `p` and group element `g`, the set of points `x` where the pattern `p` occurs (multiplicatively) at position `g` is a closed subset of `A`, provided the ambient space `A` is a T₁ topological space.

</details>

---
