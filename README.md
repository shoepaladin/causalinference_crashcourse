# causalinference_crashcourse
Causal Inference Crash Course for Scientists 

Julian Hsu
***

Causal Inference Crash Course which is a series of slides/presentations that covers the basics of causal inference. The audience is a scientist interested in learning about causal inference. This is a WiP series. 


## Covered Topics
**1. Foundations of Causal Inference** <br>
This covers how the causal inference problem can be thought of as a missing data problem. Specifically the missing counterfactual problem, based on the Potential Outcomes mental model.
**2. Defining Some ATE/ATET Causal Models** <br>
This covers some causal models for estimating the Average Treatment Effect (ATE) and Average Treatment Effect on the Treated (ATET) using cross-sectional causal models. It covers:
	- Ordinary Least Squares
	- Propensity Binning
	- Regression Adjustment
	- Double Machine Learning
	- Doubly Robust methods (in Appendix)
	- Instrumental Variables (in Appendix)
**3. ATE/ATET Inference** <br> 
This covers the high-level inference and distributional properties of causal estimators. It also discusses how and when bootstrapping is helpful.

**4. Best Practices: Outliers, Class Imbalance, Feature Selection, and Bad Control** <br> 
*Partially completed*, these slides describe the challenge of having outlier values in data on estimating causal parameters and proposes some ad-hoc solutions. 

**5. Heterogeneous Treatment Effect Models and Inference** <br> 
This describes how heterogeneous treatment effect (HTE) problems pose additional challenges on top of ATE/ATET problems. It also overviews double machine learning and tree-based HTE models.

**6. Difference-in-Difference Models for Panel Data** <br>
*WiP*

**7. Regression Discontinuity Models** <br> 
*WiP*

**8. Arguable Validation** <br> 
*WiP*

		