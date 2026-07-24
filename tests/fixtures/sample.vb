Imports System
Imports System.Collections.Generic

Namespace Acme.Services

    Public Interface IGreeter
        Function Greet(name As String) As String
    End Interface

    Public MustInherit Class BaseService
        Public Sub Log(message As String)
            Console.WriteLine(message)
        End Sub
    End Class

    Public Class AccountService
        Inherits BaseService
        Implements IGreeter, IDisposable

        Private _count As Integer

        Public Function Greet(name As String) As String Implements IGreeter.Greet
            Return "Hello " & name
        End Function

        Public Sub Dispose() Implements IDisposable.Dispose
            _count = 0
        End Sub

        Public Property Count As Integer
            Get
                Return _count
            End Get
            Set(value As Integer)
                _count = value
            End Set
        End Property
    End Class

End Namespace
