# COLIEE - Case Law data preparation
This repo contains code to aid with the case law data prep.

## Task 1 - Retrieval
For the retrieval task, the process is fully automatic: we need to run the code that grabs a sample still not used from the dataset, removes the direct citations present in the case contents and it the cases + labels to the test dataset.

## Task 2 - Entailment
For the entailment task, we need to perform a few manual steps. There is a utility UI to help with this process.
Just run task2_gui.py and it will load a "base case" (a case that cites a precedent) on the left panel, and a cited case (the aforementioned precedent) on the right panel. 
Then you need to find a fragment in the base case that is entailed by one or more paragraphs from the precedent, which requires quite a bit of a manual analysis. 
A good strategy to follow when looking for those entailment relationships is to look for "pinpoint citations" (ie, citations directly mentioning the paragraph number(s)) in the base case.
The UI will highlight in red mentions to paragraphs in the base case, so that you can quickly identify those instances and check in the precedent if the cited paragraphs do hold an entailment relationship with some fragment in the base case (which will be around that paragraph citation).
If you do find that relationship, select the entailed fragment and hit the "d" key. If there is information in the base case that can give away that entailment relationship (for example, the citation + paragraph number) you can "block" it by selecting that fragment and hitting the "b" key.
Then, on the precedent case, you need to select the paragraph(s) that entail that fragment in the base case. Just click on a paragraph, which will turn red, and then click on "e".

In each COLIEE edition, we use as training set all the cases used in the previous editions. The test set is usually comprised of 100 new cases labelled as detailed above.
