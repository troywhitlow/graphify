VERSION 5.00
Begin VB.Form frmMain
   Caption         =   "Main"
   ClientHeight    =   3000
   ClientWidth     =   4000
   Begin VB.CommandButton Command1
      Caption         =   "OK"
      Height          =   375
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   1215
   End
   Begin VB.TextBox txtName
      Height          =   285
      Left            =   120
      TabIndex        =   1
      Top             =   600
      Width           =   2895
   End
End
Attribute VB_Name = "frmMain"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
Option Explicit

Private Sub Command1_Click()
    MsgBox "Hello " & txtName.Text
End Sub

Private Sub Form_Load()
    txtName.Text = ""
End Sub
