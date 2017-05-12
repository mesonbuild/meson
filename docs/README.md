# Building the documentation

1. Get [hotdoc](https://hotdoc.github.io/installing.html) (0.8.9 required)
1. Run hotdoc in the docs/ directory:

    hotdoc run

## Upload

We are using the git-upload hotdoc plugin which basically
removes the html pages and replaces with the new content.

You can simply run:

    hotdoc run --git-upload-activate

