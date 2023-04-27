JETS
====

`credentials.json` file is required in order to run this code. It is bound to
an OAuth ID, and can be downloaded from Google API Console. With
`credentials.json` presence, the main program will display a URL to get started
with the authorization process. Once proper permissions are granted, it will be
redirected to another URL like the following:

```
http://localhost/?state=state-token&code=0AVHEtk6LxJaq6geTrPL6i2n73wCF8Y3hrVoq5VTyM2wlr3yTWYCQXMmmjaYOa-ZuHbffdA&scope=https://www.googleapis.com/auth/drive
```

This URL won't work as nothing is running on `http://localhost`. However, the
program will ask to paste a token value, which is the value of `code` in the
URL. In the example above, it's
`0AVHEtk6LxJaq6geTrPL6i2n73wCF8Y3hrVoq5VTyM2wlr3yTWYCQXMmmjaYOa-ZuHbffdA`. Copy
the value and paste it in the program. Then the value will be stored in
`token.json` file and OAuth authorization is completed.
