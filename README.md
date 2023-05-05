# causalinference_crashcourse
Causal Inference Crash Course for Scientists 

Julian Hsu
***

Causal Inference Crash Course which is a series of slides/presentations that covers the basics of causal inference. The audience is a scientist interested in learning about causal inference. This is a WiP series. 


## Covered Topics
### 1. Foundations of Causal Inference
This covers how the causal inference problem can be thought of as a missing data problem. Specifically the missing counterfactual problem, based on the Potential Outcomes mental model.
*Update 10-apr-2022* Notebook support for how causal models and traditional ML models are different.


### 2. Defining Some ATE/ATET Causal Models
This covers some causal models for estimating the Average Treatment Effect (ATE) and Average Treatment Effect on the Treated (ATET) using cross-sectional causal models. It covers:
	- Ordinary Least Squares
	- Propensity Binning
	- Regression Adjustment
	- Double Machine Learning
	- Doubly Robust methods (in Appendix)
	- Instrumental Variables (in Appendix)

### 3. ATE/ATET Inference
This covers the high-level inference and distributional properties of causal estimators. It also discusses how and when bootstrapping is helpful.

### 4. Best Practices: Outliers, Feature Selection, Bad Control, and Propensity Trimming
*Partially completed*, these slides describe the challenge of having outlier values in data on estimating causal parameters and proposes some ad-hoc solutions. 

### 5. Heterogeneous Treatment Effect Models and Inference
This describes how heterogeneous treatment effect (HTE) problems pose additional challenges on top of ATE/ATET problems. It also overviews double machine learning and tree-based HTE models.

### 6. Panel Data
This does a comparison to cross-sectional models described above, and summarizes the standard difference-in-difference (DiD) models and synthetic control (SC) models, covering three different models. These slides list references for advances topics, such as staggered DiD, and conformal inference. Synthetic DiD will be supported in a separate slide given that it builds upon concepts from DiD and SDiD.

### 7. Regression Discontinuity Models
*WiP*

### 8. Arguable Validation
We consider three types of arguable validation of causal models, from placebo testing and coefficient stability via [Oster 2013](https://www.nber.org/papers/w19054), and covariate balancing.


		